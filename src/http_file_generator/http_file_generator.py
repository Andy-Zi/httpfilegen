import json
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from prance import ResolvingParser, ValidationError

from .models import BaseURL, HttpClientBaseEnv, HttpFileData, OpenApiParser
from .models.env_file.generator import generate_env_dicts
from .models.settings.settings import Filemode, HttpSettings


def _parse_spec_content(content: str) -> Any:
    """Parse content as JSON first, then try YAML if JSON fails."""
    json_error = None
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        json_error = e

    # JSON failed, try YAML
    try:
        import yaml

        return yaml.safe_load(content)
    except ImportError:
        raise ValueError(
            "YAML support not available. Install PyYAML: pip install pyyaml"
        )
    except yaml.YAMLError as e:
        raise ValueError(
            f"Failed to parse spec content.\n"
            f"  JSON error: {json_error}\n"
            f"  YAML error: {e}"
        )
    except Exception as e:
        raise ValueError(f"Failed to parse spec content: {e}")


def load_data(file: Path | str) -> Any:
    if isinstance(file, Path):
        content = Path(file).read_text()
        data = _parse_spec_content(content)
    else:
        parsed = urlparse(file)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            try:
                with urllib.request.urlopen(file, timeout=30) as resp:
                    charset = resp.headers.get_content_charset() or "utf-8"
                    content = resp.read().decode(charset)
                data = _parse_spec_content(content)
            except urllib.error.HTTPError as e:
                raise ValueError(
                    f"HTTP error fetching spec from '{file}': {e.code} {e.reason}"
                )
            except urllib.error.URLError as e:
                raise ValueError(
                    f"Network error fetching spec from '{file}': {e.reason}"
                )
            except TimeoutError:
                raise ValueError(
                    f"Timeout fetching spec from '{file}' (30s limit exceeded)"
                )
            except Exception as e:
                raise ValueError(f"Failed to fetch spec from '{file}': {e}")
        else:
            # Treat as a local file path string
            content = Path(file).read_text()
            data = _parse_spec_content(content)

    try:
        return ResolvingParser(spec_string=json.dumps(data)).specification
    except ValidationError as e:
        # Try to recover from OpenAPI 3.1+ validation issues
        openapi_version = data.get("openapi", "unknown")
        try:
            major, minor, patch = str(openapi_version).split(".")
            if int(major) == 3 and (int(minor) > 0 or int(patch) > 0):
                data["openapi"] = "3.1.0"
                return ResolvingParser(spec_string=json.dumps(data)).specification
        except (ValueError, AttributeError):
            pass
        raise ValueError(
            f"OpenAPI validation failed (version: {openapi_version}): {e}"
        )


class HtttpFileGenerator:
    env_files: dict[Path, HttpClientBaseEnv]

    def __init__(self, file: str | Path, settings: HttpSettings | None = None) -> None:
        """Initialize with a local file path or a remote URL to an OpenAPI spec.

        settings controls generation behavior (e.g., filemode). If not provided,
        defaults are loaded (SINGLE mode by default).
        """
        data = load_data(file)
        parser = OpenApiParser(data)
        components = parser.model.components
        security_schemes = components.securitySchemes if components else None
        self.http_file = HttpFileData.from_paths(
            server=parser.model.servers,
            paths=parser.model.paths or {},
            root_security=parser.model.security,
            security_schemes=security_schemes,  # type: ignore[arg-type]
        )
        self._openapi_model = parser.model
        # Settings (defaults to SINGLE mode)
        self.settings = settings or HttpSettings()
        # If a baseURL is provided in settings, add it to the shared base URLs
        if self.settings.baseURL:
            try:
                self.http_file.base_urls.add(
                    BaseURL(value=str(self.settings.baseURL), description="")
                )
            except Exception:
                # Be defensive; if for any reason adding fails, continue with parsed servers
                pass

    def to_http_file(self, out_path: Path) -> None:
        """Write HTTP file(s) based on the configured filemode.

        - SINGLE: Write a single .http file to out_path (existing behavior).
        - MULTI:  Create a directory structure under out_path (or out_path.stem if
                  out_path looks like a file), and write one .http per API path
                  (folder structure mirrors the path segments, file named index.http).
        """
        if self.settings.filemode == Filemode.SINGLE:
            lines = self.http_file.to_http_file(
                include_examples=self.settings.include_examples,
                include_schema=self.settings.include_schema,
                editor_mode=self.settings.editor_mode,
            )
            with Path.open(out_path, "w") as f:
                # Using write for a single string payload
                f.write(lines)
            return

        # MULTI mode: derive an output directory from out_path
        if out_path.suffix == ".http":
            out_dir = out_path.parent / out_path.stem
        else:
            out_dir = out_path
        self.to_http_files(out_dir)

    def to_env_files(
        self, public_out: Path, private_out: Path, env_name: str = "dev"
    ) -> bool:
        """
        Generate http-client.env.json and http-client.private.env.json skeletons
        based on the OpenAPI security schemes.

        Returns:
            True if a valid base URL was found, False if placeholder was used.
        """
        servers = self._openapi_model.servers or []
        base_url_override = (
            str(self.settings.baseURL) if self.settings.baseURL else None
        )

        public_env, private_env, has_valid_base_url = generate_env_dicts(
            self._openapi_model,
            env_name=env_name,
            servers=servers,
            base_url_override=base_url_override,
        )
        with Path.open(public_out, "w") as f:
            json.dump(public_env, f, indent=2)
        with Path.open(private_out, "w") as f:
            json.dump(private_env, f, indent=2)

        return has_valid_base_url

    # --- Multi-file helpers ---
    def _group_requests_by_path(self) -> dict[str, list]:
        """Group HttpRequest objects by their base path (without query lines).

        Some paths may contain newlines with query placeholders; only the first
        line (the actual path) is used for grouping and directory structure.
        """
        groups: dict[str, list] = {}
        for req in self.http_file.requests:
            base_path = req.path.split("\n", 1)[0]
            groups.setdefault(base_path, []).append(req)
        return groups

    def to_http_files(self, out_dir: Path, filename: str = "index.http") -> None:
        """Write one .http file per API path under out_dir.

        The directory structure mirrors the path segments. For example, a path
        like "/api/v1/users/{id}" will be written to:
            out_dir/api/v1/users/{id}/index.http
        The file content includes the shared block and all methods for that path.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        groups = self._group_requests_by_path()
        for path, reqs in groups.items():
            # Normalize and split path into segments, ignoring leading '/'
            parts = [seg for seg in path.split("/") if seg]
            target_dir = out_dir
            for seg in parts:
                target_dir = target_dir / seg
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / filename

            data = HttpFileData(base_urls=self.http_file.base_urls, requests=reqs)
            content = data.to_http_file(
                include_examples=self.settings.include_examples,
                include_schema=self.settings.include_schema,
                editor_mode=self.settings.editor_mode,
            )
            with Path.open(target_file, "w") as f:
                f.write(content)
