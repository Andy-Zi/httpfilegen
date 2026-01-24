import json
from pathlib import Path
from typing import Any, NoReturn
from pydantic_core import Url

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import typer

from http_file_generator import HtttpFileGenerator
from http_file_generator.models import METHOD, Filemode, EditorMode, HttpSettings, OpenApiParser

app = typer.Typer(
    help="Generate .http files and env files from an OpenAPI spec.",
    no_args_is_help=True,
    add_completion=False,
)


def _abort(msg: str, code: int = 1) -> NoReturn:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    raise typer.Exit(code)


def _json_print(data: Any) -> None:
    typer.echo(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _is_url(s: str | Path) -> bool:
    """Check if the given value is a URL (starts with http:// or https://)."""
    if isinstance(s, Path):
        return False
    return s.startswith("http://") or s.startswith("https://")


def _validate_spec_source(spec: str | Path) -> str | Path:
    """Validate spec source exists (for file paths) or return as-is (for URLs)."""
    if _is_url(spec):
        return spec
    p = spec if isinstance(spec, Path) else Path(spec)
    if not p.exists() or not p.is_file():
        _abort(f"Spec file not found: {spec}")
    return p


def _ensure_write_target(path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        _abort(f"Refusing to overwrite existing file without --overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict[str, Any]:
    """Load configuration from ~/.config/httpfilegen/config.toml if it exists."""
    config_path = Path.home() / ".config" / "httpfilegen" / "config.toml"
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        # If config file is unreadable or malformed, ignore it
        return {}


def _get_config_value(config: dict[str, Any], key: str, default: Any = None) -> Any:
    """Get a value from config, with optional defaults section."""
    if "defaults" in config and key in config["defaults"]:
        return config["defaults"][key]
    return config.get(key, default)


def _method_upper_list(methods: list[str] | None) -> list[str] | None:
    if methods is None:
        return None
    result: list[str] = []
    for m in methods:
        mu = m.upper()
        if mu not in METHOD.__members__ and mu not in {e.value for e in METHOD}:
            _abort(f"Unknown method: {m}")
        result.append(mu)
    return result


def _parse_filemode(value: str | None) -> Filemode:
    if value is None:
        return Filemode.SINGLE
    v = value.strip().lower()
    if v in ("single", "s"):
        return Filemode.SINGLE
    if v in ("multi", "m"):
        return Filemode.MULTI
    _abort("Invalid value for --filemode: choose 'single' or 'multi'.")


def _parse_editor_mode(value: str | None) -> EditorMode:
    if value is None:
        return EditorMode.DEFAULT
    v = value.strip().lower()
    if v in ("default", "d"):
        return EditorMode.DEFAULT
    if v in ("kulala", "k"):
        return EditorMode.KULALA
    if v in ("pycharm", "intellij", "jetbrains", "p"):
        return EditorMode.PYCHARM
    if v in ("httpyac", "vscode", "h", "v"):
        return EditorMode.HTTPYAC
    _abort(
        "Invalid value for --mode: choose 'default', 'kulala', 'pycharm', or 'httpyac'."
    )


@app.command("generate")
def generate(
    spec=typer.Argument(..., help="Path or URL to the OpenAPI spec (yaml/json)."),
    out=typer.Option(
        None,
        "--out",
        "-o",
        help="Output .http file path. Defaults to <spec>.http next to the spec.",
    ),
    filemode=typer.Option(
        None,
        "--filemode",
        "-f",
        help="File generation mode: SINGLE (one .http) or MULTI (one per path).",
    ),
    base_url=typer.Option(
        None,
        "--base-url",
        help="Optional base URL to include in generated .http files.",
    ),
    mode: str = typer.Option(
        "default",
        "--mode",
        help="Editor mode: default (cross-compatible), kulala (Neovim), pycharm (JetBrains), vscode (httpyac).",
    ),
    include_examples: bool = typer.Option(
        False,
        "--include-examples/--no-include-examples",
        help="Include commented response examples next to each request.",
    ),
    include_schema: bool = typer.Option(
        False,
        "--include-schema/--no-include-schema",
        help="Include commented request body examples next to each request.",
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite/--no-overwrite", help="Overwrite existing files if present."
    ),
    env: bool = typer.Option(
        True,
        "--env/--no-env",
        help="Also generate http-client.env.json and http-client.private.env.json.",
    ),
    env_name: str = typer.Option(
        "dev", "--env-name", help="Environment section name for env files."
    ),
    env_dir=typer.Option(
        None,
        "--env-dir",
        "-d",
        help="Directory where env files will be written (defaults to .http file directory).",
    ),
    public_env_filename: str = typer.Option(
        "http-client.env.json", "--public-env-filename", help="Public env filename."
    ),
    private_env_filename: str = typer.Option(
        "http-client.private.env.json",
        "--private-env-filename",
        help="Private env filename.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview output without writing any files.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress informational output (only show errors and file paths).",
    ),
) -> None:
    """
    Generate a .http file from an OpenAPI spec.
    Optionally also generate http-client env files.
    """
    # Load configuration and apply defaults
    config = _load_config()

    # Apply defaults if not explicitly provided
    if mode == "default":  # Only override if using default
        config_mode = _get_config_value(config, "mode")
        if config_mode:
            mode = str(config_mode)
    if filemode is None:
        config_filemode = _get_config_value(config, "filemode")
        if config_filemode:
            filemode = str(config_filemode)
    if base_url is None:
        config_base_url = _get_config_value(config, "base_url")
        if config_base_url:
            base_url = str(config_base_url)
    if env_name == "dev":  # Only override if using default
        config_env_name = _get_config_value(config, "env_name")
        if config_env_name:
            env_name = str(config_env_name)
    if not include_examples:  # Only override if False (default)
        config_examples = _get_config_value(config, "include_examples")
        if config_examples is True:
            include_examples = True
    if not include_schema:  # Only override if False (default)
        config_schema = _get_config_value(config, "include_schema")
        if config_schema is True:
            include_schema = True

    spec = _validate_spec_source(spec)
    # Derive output path (file or directory depending on filemode)
    if out is not None:
        out_path = Path(out)
    elif _is_url(spec):
        # derive name from URL path segment
        name = Path(str(spec).rstrip("/").split("/")[-1]).stem or "openapi"
        out_path = Path.cwd() / f"{name}.http"
    else:
        out_path = Path(spec).with_suffix(".http")

    try:
        fm = _parse_filemode(filemode)
        em = _parse_editor_mode(mode)
        settings = HttpSettings(
            filemode=fm,
            baseURL=Url(base_url) if base_url else None,
            include_examples=include_examples,
            include_schema=include_schema,
            editor_mode=em,
        )
        gen = HtttpFileGenerator(spec, settings=settings)
    except Exception as e:
        _abort(f"Failed to parse spec: {e}")

    # Dry-run mode: preview output without writing
    if dry_run:
        typer.secho("=== DRY RUN MODE ===", fg=typer.colors.YELLOW, bold=True)
        typer.secho(f"\nWould write to: {out_path}", fg=typer.colors.CYAN)
        if fm == Filemode.MULTI:
            target_dir = (
                out_path.parent / out_path.stem
                if out_path.suffix == ".http"
                else out_path
            )
            typer.secho(f"Mode: MULTI (directory: {target_dir})", fg=typer.colors.CYAN)
        else:
            typer.secho("Mode: SINGLE", fg=typer.colors.CYAN)

        typer.secho("\n--- HTTP File Content Preview ---", fg=typer.colors.BLUE)
        content = gen.http_file.to_http_file(
            include_examples=settings.include_examples,
            include_schema=settings.include_schema,
            editor_mode=settings.editor_mode,
        )
        # Show first 100 lines or full content if shorter
        lines = content.splitlines()
        preview_lines = lines[:100]
        typer.echo("\n".join(preview_lines))
        if len(lines) > 100:
            typer.secho(
                f"\n... ({len(lines) - 100} more lines truncated)",
                fg=typer.colors.YELLOW,
            )

        if env:
            env_target_dir = env_dir or out_path.parent
            typer.secho(
                f"\nWould also generate env files in: {env_target_dir}",
                fg=typer.colors.CYAN,
            )
            typer.echo(f"  - {public_env_filename}")
            typer.echo(f"  - {private_env_filename}")

        typer.secho("\n=== END DRY RUN ===", fg=typer.colors.YELLOW, bold=True)
        return

    # Ensure write target based on mode
    if fm == Filemode.SINGLE:
        _ensure_write_target(out_path, overwrite)
        try:
            gen.to_http_file(out_path)
        except Exception as e:
            _abort(f"Failed to write HTTP file: {e}")
        if not quiet:
            typer.secho(f"HTTP file generated: {out_path}", fg=typer.colors.GREEN)
        default_env_dir = out_path.parent
    else:
        # MULTI mode: resolve target directory
        target_dir = (
            out_path.parent / out_path.stem if out_path.suffix == ".http" else out_path
        )
        if target_dir.exists() and not overwrite:
            _abort(
                f"Refusing to overwrite existing directory without --overwrite: {target_dir}"
            )
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            gen.to_http_file(target_dir)
        except Exception as e:
            _abort(f"Failed to write HTTP files: {e}")
        if not quiet:
            typer.secho(f"HTTP files generated under: {target_dir}", fg=typer.colors.GREEN)
        default_env_dir = target_dir

    if env:
        env_target_dir = env_dir or default_env_dir
        public_env = env_target_dir / public_env_filename
        private_env = env_target_dir / private_env_filename
        if not overwrite:
            if public_env.exists():
                _abort(f"Public env file already exists, use --overwrite: {public_env}")
            if private_env.exists():
                _abort(
                    f"Private env file already exists, use --overwrite: {private_env}"
                )
        public_env.parent.mkdir(parents=True, exist_ok=True)
        try:
            has_valid_base_url = gen.to_env_files(public_env, private_env, env_name=env_name)
        except Exception as e:
            _abort(f"Failed to write env files: {e}")
        if not quiet:
            typer.secho(
                f"Env files generated: {public_env}, {private_env}", fg=typer.colors.GREEN
            )
        if not has_valid_base_url:
            typer.secho(
                "\nWarning: No valid base URL found in the OpenAPI spec.",
                fg=typer.colors.YELLOW,
                bold=True,
            )
            typer.echo(
                "  The env file contains a placeholder. Please update BASE_URL manually."
            )
            typer.echo(f"  Edit: {public_env}")

    # Inform about tool compatibility (unless quiet mode)
    if not quiet:
        typer.secho("\n Tool Compatibility:", fg=typer.colors.BLUE, bold=True)
        typer.echo(" Kulala (Neovim): Full support including environment files")
        typer.echo(" PyCharm/IntelliJ: Full support with JetBrains HTTP Client")
        typer.echo(
            " httpyac (VS Code): Full support - use httpyac extension, not REST Client"
        )
        typer.echo(
            " VS Code REST Client: Limited support - environment variables need manual setup"
        )
        typer.echo("\n BASE_URL is now managed per-environment in the env files!")


@app.command("env")
def gen_env(
    spec: str = typer.Argument(
        ..., help="Path or URL to the OpenAPI spec (yaml/json)."
    ),
    out_dir: Path | None = typer.Option(
        None,
        "--out-dir",
        "-d",
        help="Directory where env files will be written. Defaults to the spec directory.",
    ),
    env_name: str = typer.Option("dev", "--env-name", help="Environment section name."),
    overwrite: bool = typer.Option(
        False, "--overwrite/--no-overwrite", help="Overwrite existing env files."
    ),
    public_env_filename: str = typer.Option(
        "http-client.env.json", "--public-env-filename", help="Public env filename."
    ),
    private_env_filename: str = typer.Option(
        "http-client.private.env.json",
        "--private-env-filename",
        help="Private env filename.",
    ),
) -> None:
    """
    Generate only http-client env files from the OpenAPI security schemes.
    """
    spec = _validate_spec_source(spec)
    try:
        gen = HtttpFileGenerator(spec)
    except Exception as e:
        _abort(f"Failed to parse spec: {e}")
    target_dir = out_dir or (Path.cwd() if _is_url(spec) else Path(spec).parent)
    public_env = target_dir / public_env_filename
    private_env = target_dir / private_env_filename
    _ensure_write_target(public_env, overwrite)
    _ensure_write_target(private_env, overwrite)
    try:
        has_valid_base_url = gen.to_env_files(public_env, private_env, env_name=env_name)
    except Exception as e:
        _abort(f"Failed to write env files: {e}")
    typer.secho(
        f"Env files generated: {public_env}, {private_env}", fg=typer.colors.GREEN
    )
    if not has_valid_base_url:
        typer.secho(
            "\nWarning: No valid base URL found in the OpenAPI spec.",
            fg=typer.colors.YELLOW,
            bold=True,
        )
        typer.echo(
            "  The env file contains a placeholder. Please update BASE_URL manually."
        )
        typer.echo(f"  Edit: {public_env}")


@app.command("info")
def info(
    spec: str = typer.Argument(
        ..., help="Path or URL to the OpenAPI spec (yaml/json)."
    ),
    json_out: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Print a summary of the OpenAPI spec: servers, paths, methods, and security schemes.
    """
    spec = _validate_spec_source(spec)
    try:
        parser = OpenApiParser(spec)
    except Exception as e:
        _abort(f"Failed to parse spec: {e}")

    servers = [
        {"url": s.url, "description": s.description or ""}
        for s in (parser.model.servers or [])
    ]
    paths_dict = parser.model.paths or {}
    total_paths = len(paths_dict)
    method_counts: dict[str, int] = {}
    for p, item in paths_dict.items():
        for m in METHOD:
            if getattr(item, m.lower(), None) is not None:
                method_counts[m.value] = method_counts.get(m.value, 0) + 1
    comps = getattr(parser.model, "components", None)
    sec_schemes = getattr(comps, "securitySchemes", None) if comps else None
    security = []
    if sec_schemes:
        for name, scheme in sec_schemes.items():
            stype = getattr(scheme, "type", None)
            security.append({"name": name, "type": stype})

    payload = {
        "servers": servers,
        "total_paths": total_paths,
        "method_counts": method_counts,
        "security_schemes": security,
    }
    if json_out:
        _json_print(payload)
    else:
        typer.secho("Servers:", fg=typer.colors.CYAN, bold=True)
        for s in servers:
            typer.echo(
                f"  - {s['url']}  {('(' + s['description'] + ')') if s['description'] else ''}"
            )
        typer.secho(f"\nPaths: {total_paths}", fg=typer.colors.CYAN, bold=True)
        if method_counts:
            typer.secho("Operations by method:", fg=typer.colors.CYAN, bold=True)
            for k in sorted(method_counts.keys()):
                typer.echo(f"  {k:<7} {method_counts[k]}")
        if security:
            typer.secho("\nSecurity Schemes:", fg=typer.colors.CYAN, bold=True)
            for s in security:
                typer.echo(f"  - {s['name']}: {s['type']}")


@app.command("validate")
def validate(
    spec: str = typer.Argument(
        ..., help="Path or URL to the OpenAPI spec (yaml/json)."
    ),
    json_out: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """
    Validate an OpenAPI spec without generating any files.

    Checks that the spec is valid YAML/JSON and conforms to OpenAPI 3.x schema.
    Returns exit code 0 on success, 1 on failure.
    """
    spec = _validate_spec_source(spec)
    errors: list[str] = []

    try:
        parser = OpenApiParser(spec)
    except Exception as e:
        errors.append(str(e))

    if errors:
        if json_out:
            _json_print({"valid": False, "errors": errors})
        else:
            typer.secho("Validation FAILED", fg=typer.colors.RED, bold=True)
            for err in errors:
                typer.echo(f"  - {err}")
        raise typer.Exit(1)

    # Gather spec info for successful validation
    info_data = parser.model.info
    openapi_version = getattr(parser.model, "openapi", "unknown")
    paths_count = len(parser.model.paths or {})
    servers_count = len(parser.model.servers or [])

    if json_out:
        _json_print({
            "valid": True,
            "openapi_version": openapi_version,
            "title": info_data.title if info_data else None,
            "version": info_data.version if info_data else None,
            "paths_count": paths_count,
            "servers_count": servers_count,
        })
    else:
        typer.secho("Validation OK", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"  OpenAPI version: {openapi_version}")
        if info_data:
            typer.echo(f"  Title: {info_data.title}")
            typer.echo(f"  Version: {info_data.version}")
        typer.echo(f"  Paths: {paths_count}")
        typer.echo(f"  Servers: {servers_count}")


@app.command("paths")
def list_paths(
    spec: str = typer.Argument(
        ..., help="Path or URL to the OpenAPI spec (yaml/json)."
    ),
    method: list[str] | None = typer.Option(
        None,
        "--method",
        "-m",
        help="Filter by HTTP method; can be passed multiple times.",
    ),
    with_methods: bool = typer.Option(
        True, "--with-methods/--no-with-methods", help="Show methods next to each path."
    ),
) -> None:
    """
    List all paths in the spec, optionally filtered by HTTP methods.
    """
    spec = _validate_spec_source(spec)
    methods = _method_upper_list(method)
    try:
        parser = OpenApiParser(spec)
    except Exception as e:
        _abort(f"Failed to parse spec: {e}")
    paths = parser.model.paths or {}
    for p, item in paths.items():
        available = [
            m.value for m in METHOD if getattr(item, m.lower(), None) is not None
        ]
        if methods and not any(m in available for m in methods):
            continue
        if with_methods:
            typer.echo(f"{', '.join(available):<30} {p}")
        else:
            typer.echo(p)


@app.command("sample")
def sample(
    spec: str = typer.Argument(
        ..., help="Path or URL to the OpenAPI spec (yaml/json)."
    ),
    path: str = typer.Argument(..., help="The API path to inspect, e.g. /users/{id}."),
    method: str | None = typer.Option(
        None, "--method", "-m", help="HTTP method to show. Defaults to all."
    ),
    request: bool = typer.Option(
        True, "--request/--no-request", help="Include request body samples."
    ),
    response: bool = typer.Option(
        True, "--response/--no-response", help="Include response body samples."
    ),
    status: str | None = typer.Option(
        None, "--status", help="Filter a specific response HTTP status."
    ),
    content_type: str | None = typer.Option(
        None,
        "--content-type",
        help="Filter a specific content type.",
    ),
) -> None:
    """
    Print generated request/response body samples for a path (and optionally a method).
    """
    spec = _validate_spec_source(spec)
    m_upper = method.upper() if method else None
    if m_upper and (
        m_upper not in METHOD.__members__.keys()
        and m_upper not in {e.value for e in METHOD}
    ):
        _abort(f"Unknown method: {method}")
    try:
        parser = OpenApiParser(spec)
        # Validate path exists
        parser.get_path_item(path)
    except Exception as e:
        _abort(f"Failed to parse spec or find path: {e}")

    result: dict[str, Any] = {"path": path}
    if request:
        reqs = parser.get_request_body(path)
        if m_upper:
            reqs = {m_upper: reqs.get(m_upper)}
        if content_type:
            filt: dict[str, Any] = {}
            for m, body in reqs.items():
                if not body:
                    filt[m] = None
                elif content_type in body:
                    filt[m] = {content_type: body[content_type]}
                else:
                    filt[m] = None
            reqs = filt
        result["request"] = reqs
    if response:
        resps = parser.get_response_body(path)
        if m_upper:
            resps = {m_upper: resps.get(m_upper, {})}
        if status:
            resps = {
                m: ({status: bodies.get(status)} if bodies else {})
                for m, bodies in resps.items()
            }
        if content_type:
            filt_resp: dict[str, Any] = {}
            for m, bodies in resps.items():
                if not bodies:
                    filt_resp[m] = {}
                    continue
                new_status_map: dict[str, Any] = {}
                for st, cts in bodies.items():
                    if cts and content_type in cts:
                        new_status_map[st] = {content_type: cts[content_type]}
                filt_resp[m] = new_status_map
            resps = filt_resp
        result["response"] = resps

    _json_print(result)


@app.command("batch")
def batch(
    input_path: Path = typer.Argument(
        ..., help="Path to a directory of specs or a single spec file."
    ),
    pattern: str = typer.Option(
        "*.json,*.yaml,*.yml",
        "--pattern",
        "-p",
        help="Glob(s) for spec files, comma-separated.",
    ),
    filemode: str | None = typer.Option(
        None,
        "--filemode",
        "-f",
        help="File generation mode: SINGLE (one .http) or MULTI (one per path).",
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help="Optional base URL to include in generated .http files.",
    ),
    mode: str = typer.Option(
        "default",
        "--mode",
        help="Editor mode: default, kulala, pycharm, or httpyac.",
    ),
    include_examples: bool = typer.Option(
        False,
        "--include-examples/--no-include-examples",
        help="Include commented response examples next to each request.",
    ),
    include_schema: bool = typer.Option(
        False,
        "--include-schema/--no-include-schema",
        help="Include commented request body examples next to each request.",
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite/--no-overwrite", help="Overwrite outputs if they exist."
    ),
    env: bool = typer.Option(
        True, "--env/--no-env", help="Also generate env files for each spec."
    ),
    env_name: str = typer.Option("dev", "--env-name", help="Environment section name."),
) -> None:
    """
    Process a directory of OpenAPI specs (or a single file) and generate .http (+ env) for each.
    """
    processed = 0
    failures: list[dict[str, str]] = []

    files: list[Path] = []
    if input_path.is_file():
        files = [input_path]
    elif input_path.is_dir():
        pats = [p.strip() for p in pattern.split(",") if p.strip()]
        for pat in pats:
            files.extend(input_path.glob(pat))
        files = sorted(set(files))
    else:
        _abort(f"Path not found: {input_path}")

    if not files:
        _abort("No spec files found to process.")

    for spec in files:
        spec = spec.resolve()
        try:
            fm = _parse_filemode(filemode)
            em = _parse_editor_mode(mode)
            settings = HttpSettings(
                filemode=fm,
                baseURL=Url(base_url) if base_url else None,
                include_examples=include_examples,
                include_schema=include_schema,
                editor_mode=em,
            )
            gen = HtttpFileGenerator(spec, settings=settings)
            if fm == Filemode.SINGLE:
                out_file = spec.with_suffix(".http")
                _ensure_write_target(out_file, overwrite)
                content = gen.http_file.to_http_file(
                    include_examples=settings.include_examples,
                    include_schema=settings.include_schema,
                    editor_mode=settings.editor_mode,
                )
                out_file.write_text(content)
                env_base_dir = spec.parent
            else:
                target_dir = spec.parent / spec.stem
                if target_dir.exists() and not overwrite:
                    raise RuntimeError(
                        f"Refusing to overwrite existing directory without --overwrite: {target_dir}"
                    )
                target_dir.mkdir(parents=True, exist_ok=True)
                gen.to_http_file(target_dir)
                env_base_dir = target_dir
            if env:
                public_env = env_base_dir / "http-client.env.json"
                private_env = env_base_dir / "http-client.private.env.json"
                if overwrite or (not public_env.exists() and not private_env.exists()):
                    gen.to_env_files(public_env, private_env, env_name=env_name)
            processed += 1
            if fm == Filemode.SINGLE:
                typer.secho(f"Generated: {out_file}", fg=typer.colors.GREEN)
            else:
                typer.secho(
                    f"Generated (MULTI): {spec} -> {env_base_dir}",
                    fg=typer.colors.GREEN,
                )
        except Exception as e:
            failures.append({"spec": str(spec), "error": str(e)})
            typer.secho(f"Failed: {spec} -> {e}", fg=typer.colors.RED)

    typer.echo("")
    typer.secho(
        f"Done. OK: {processed}  Failed: {len(failures)}",
        fg=typer.colors.CYAN,
        bold=True,
    )
    if failures:
        for f in failures:
            typer.echo(f"  - {f['spec']}: {f['error']}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
