from pathlib import Path

from .models import HttpFileData, HttpClientBaseEnv, OpenApiParser, BaseURL
from .models.settings.settings import HttpSettings, Filemode
from .models.env_file.generator import generate_env_dicts
import json


class HtttpFileGenerator:
    env_files: dict[Path, HttpClientBaseEnv]

    def __init__(self, file: str | Path, settings: HttpSettings | None = None):
        """Initialize with a local file path or a remote URL to an OpenAPI spec.

        settings controls generation behavior (e.g., filemode). If not provided,
        defaults are loaded (SINGLE mode by default).
        """
        parser = OpenApiParser(file)
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

    def to_http_file(self, out_path: Path):
        """Write HTTP file(s) based on the configured filemode.

        - SINGLE: Write a single .http file to out_path (existing behavior).
        - MULTI:  Create a directory structure under out_path (or out_path.stem if
                  out_path looks like a file), and write one .http per API path
                  (folder structure mirrors the path segments, file named index.http).
        """
        if self.settings.filemode == Filemode.SINGLE:
            lines = self.http_file.to_http_file()
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

    def to_env_files(self, public_out: Path, private_out: Path, env_name: str = "dev"):
        """
        Generate http-client.env.json and http-client.private.env.json skeletons
        based on the OpenAPI security schemes.
        """
        public_env, private_env = generate_env_dicts(
            self._openapi_model, env_name=env_name
        )
        with Path.open(public_out, "w") as f:
            json.dump(public_env, f, indent=2)
        with Path.open(private_out, "w") as f:
            json.dump(private_env, f, indent=2)

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

    def to_http_files(self, out_dir: Path, filename: str = "index.http"):
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
            content = data.to_http_file()
            with Path.open(target_file, "w") as f:
                f.write(content)
