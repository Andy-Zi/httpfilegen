import json
import re
from pathlib import Path
from typing import Any

from .models import BaseURL, HttpClientBaseEnv, HttpFileData, OpenApiParser
from .models.env_file.generator import (
    generate_env_dicts,
    has_base_url_placeholder,
    merge_env_dicts,
)
from .models.settings.settings import Filemode, HttpSettings
from .spec_loader import _parse_spec_content, load_data  # noqa: F401

_PATH_PARAM = re.compile(r"\{\{?([^{}]+?)\}?\}")


def _directory_names(paths: list[list[str]]) -> dict[tuple[str, ...], str]:
    """Map each path prefix to a shell-safe directory name for its last segment.

    Path parameters (``{id}`` or ``{{id}}``) become ``_id_``. If a literal
    sibling segment already has that name (compared case-insensitively for
    case-insensitive filesystems), more underscores are added until it is unique.
    """
    literals: dict[tuple[str, ...], set[str]] = {}
    for parts in paths:
        for i, seg in enumerate(parts):
            if not _PATH_PARAM.search(seg):
                literals.setdefault(tuple(parts[:i]), set()).add(seg.casefold())

    names: dict[tuple[str, ...], str] = {}
    for parts in paths:
        for i, seg in enumerate(parts):
            key = tuple(parts[: i + 1])
            if key in names:
                continue
            if not _PATH_PARAM.search(seg):
                names[key] = seg
                continue
            taken = literals.get(tuple(parts[:i]), set())
            pad = "_"
            while True:
                name = _PATH_PARAM.sub(lambda m: f"{pad}{m.group(1)}{pad}", seg)
                if name.casefold() not in taken:
                    break
                pad += "_"
            names[key] = name
    return names


def _read_env_file(path: Path) -> dict[str, Any]:
    """Return the JSON object stored at ``path``, or ``{}`` if it does not exist."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Cannot merge into invalid JSON env file {path}: {e}")
    if not isinstance(data, dict):
        raise ValueError(f"Cannot merge into env file without a JSON object: {path}")
    return data


class HtttpFileGenerator:
    env_files: dict[Path, HttpClientBaseEnv]

    def __init__(
        self,
        file: str | Path,
        settings: HttpSettings | None = None,
        override: Path | None = None,
    ) -> None:
        """Initialize with a local file path or a remote URL to an OpenAPI spec.

        settings controls generation behavior (e.g., filemode). If not provided,
        defaults are loaded (SINGLE mode by default). override is a merge-patch
        file applied to the spec before it is resolved.
        """
        data = load_data(file, override)
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

        Existing files are merged with ``merge_env_dicts``: values the user filled
        in, and keys or environments the generator does not produce, are kept.

        Returns:
            False if a BASE_URL placeholder remains in the public env, else True.
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
        public_env = merge_env_dicts(_read_env_file(public_out), public_env)
        private_env = merge_env_dicts(_read_env_file(private_out), private_env)
        with Path.open(public_out, "w") as f:
            json.dump(public_env, f, indent=2)
        with Path.open(private_out, "w") as f:
            json.dump(private_env, f, indent=2)

        return has_valid_base_url or not has_base_url_placeholder(public_env)

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

        The directory structure mirrors the path segments, with path parameters
        written as "_name_" so no directory needs shell quoting. For example, a
        path like "/api/v1/users/{id}" will be written to:
            out_dir/api/v1/users/_id_/index.http
        The request URLs inside the file keep the "{{id}}" variable.
        The file content includes the shared block and all methods for that path.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        groups = self._group_requests_by_path()
        # Normalize and split paths into segments, ignoring leading '/'
        segments = {path: [seg for seg in path.split("/") if seg] for path in groups}
        dir_names = _directory_names(list(segments.values()))
        for path, reqs in groups.items():
            parts = segments[path]
            target_dir = out_dir
            for i in range(len(parts)):
                target_dir = target_dir / dir_names[tuple(parts[: i + 1])]
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
