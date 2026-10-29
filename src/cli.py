import json
import warnings
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
from http_file_generator.models.env_file.generator import EnvAuthWarning
from http_file_generator.overrides import (
    DEFAULT_ADDED_SCHEME,
    PLACEHOLDER_TOKEN_URL,
    add_oauth2_patch,
    bearer_to_oauth2_patch,
    default_override_path,
    dump_document,
    find_override,
    is_override_file,
    load_document,
)

app = typer.Typer(
    help="Generate .http files and env files from an OpenAPI spec.",
    no_args_is_help=True,
    add_completion=False,
)
override_app = typer.Typer(
    help="Create spec override files (<spec>_override.{yaml,yml,json}).",
    no_args_is_help=True,
)
app.add_typer(override_app, name="override")

OVERRIDE_HELP = (
    "Merge-patch file applied to the spec. "
    "Defaults to <spec>_override.{yaml,yml,json} next to the spec."
)
NO_OVERRIDE_HELP = "Ignore any override file next to the spec."


def _abort(msg: str, code: int = 1) -> NoReturn:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    raise typer.Exit(code)


def _write_env_files(
    gen: HtttpFileGenerator, public_env: Path, private_env: Path, env_name: str
) -> bool:
    """Write env files and print a warning for each auth config that was dropped or incomplete."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", EnvAuthWarning)
        has_valid_base_url = gen.to_env_files(public_env, private_env, env_name=env_name)
    for w in caught:
        if issubclass(w.category, EnvAuthWarning):
            typer.secho(f"Warning: {w.message}", fg=typer.colors.YELLOW, err=True)
        else:
            warnings.showwarning(w.message, w.category, w.filename, w.lineno)
    return has_valid_base_url


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


def _resolve_override(
    spec: str | Path, override: Path | None, no_override: bool, quiet: bool = False
) -> Path | None:
    """Pick the explicit override, else auto-detect one next to a local spec."""
    if override is not None:
        if not override.is_file():
            _abort(f"Override file not found: {override}")
        resolved: Path | None = override
    elif no_override or _is_url(spec):
        resolved = None
    else:
        resolved = find_override(Path(spec))
    if resolved is not None and not quiet:
        typer.secho(f"Using override: {resolved}", fg=typer.colors.CYAN, err=True)
    return resolved


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


def _apply_config_defaults(
    mode: str | None,
    filemode: str | None,
    base_url: str | None,
    env_name: str | None,
    include_examples: bool | None,
    include_schema: bool | None,
) -> tuple[str, str | None, str | None, str, bool, bool]:
    """Fill options not given on the command line (None) from the config file.

    Options missing from both fall back to the defaults shown in ``--help``.
    """
    config = _load_config()

    if mode is None:
        mode = str(_get_config_value(config, "mode") or "default")
    if filemode is None:
        config_filemode = _get_config_value(config, "filemode")
        if config_filemode:
            filemode = str(config_filemode)
    if base_url is None:
        config_base_url = _get_config_value(config, "base_url")
        if config_base_url:
            base_url = str(config_base_url)
    if env_name is None:
        env_name = str(_get_config_value(config, "env_name") or "dev")
    if include_examples is None:
        include_examples = _get_config_value(config, "include_examples") is True
    if include_schema is None:
        include_schema = _get_config_value(config, "include_schema") is True

    return mode, filemode, base_url, env_name, include_examples, include_schema


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
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Editor mode: default (cross-compatible), kulala (Neovim), pycharm (JetBrains), vscode (httpyac).",
        show_default="default",
    ),
    include_examples: bool | None = typer.Option(
        None,
        "--include-examples/--no-include-examples",
        help="Include commented response examples next to each request.",
        show_default="no-include-examples",
    ),
    include_schema: bool | None = typer.Option(
        None,
        "--include-schema/--no-include-schema",
        help="Include commented request body examples next to each request.",
        show_default="no-include-schema",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite/--no-overwrite",
        help="Overwrite existing .http files. Existing env files are always merged.",
    ),
    env: bool = typer.Option(
        True,
        "--env/--no-env",
        help="Also generate http-client.env.json and http-client.private.env.json.",
    ),
    env_name: str | None = typer.Option(
        None,
        "--env-name",
        help="Environment section name for env files.",
        show_default="dev",
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
    override: Path | None = typer.Option(None, "--override", help=OVERRIDE_HELP),
    no_override: bool = typer.Option(False, "--no-override", help=NO_OVERRIDE_HELP),
) -> None:
    """
    Generate a .http file from an OpenAPI spec.
    Optionally also generate http-client env files.
    """
    mode, filemode, base_url, env_name, include_examples, include_schema = (
        _apply_config_defaults(
            mode, filemode, base_url, env_name, include_examples, include_schema
        )
    )

    spec = _validate_spec_source(spec)
    override_path = _resolve_override(spec, override, no_override, quiet)
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
        gen = HtttpFileGenerator(spec, settings=settings, override=override_path)
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
        public_env.parent.mkdir(parents=True, exist_ok=True)
        try:
            has_valid_base_url = _write_env_files(gen, public_env, private_env, env_name)
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
        False,
        "--overwrite/--no-overwrite",
        help="Has no effect: existing env files are always merged.",
        hidden=True,
    ),
    public_env_filename: str = typer.Option(
        "http-client.env.json", "--public-env-filename", help="Public env filename."
    ),
    private_env_filename: str = typer.Option(
        "http-client.private.env.json",
        "--private-env-filename",
        help="Private env filename.",
    ),
    override: Path | None = typer.Option(None, "--override", help=OVERRIDE_HELP),
    no_override: bool = typer.Option(False, "--no-override", help=NO_OVERRIDE_HELP),
) -> None:
    """
    Generate only http-client env files from the OpenAPI security schemes.
    """
    spec = _validate_spec_source(spec)
    override_path = _resolve_override(spec, override, no_override)
    try:
        gen = HtttpFileGenerator(spec, override=override_path)
    except Exception as e:
        _abort(f"Failed to parse spec: {e}")
    target_dir = out_dir or (Path.cwd() if _is_url(spec) else Path(spec).parent)
    public_env = target_dir / public_env_filename
    private_env = target_dir / private_env_filename
    try:
        has_valid_base_url = _write_env_files(gen, public_env, private_env, env_name)
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
    override: Path | None = typer.Option(None, "--override", help=OVERRIDE_HELP),
    no_override: bool = typer.Option(False, "--no-override", help=NO_OVERRIDE_HELP),
) -> None:
    """
    Print a summary of the OpenAPI spec: servers, paths, methods, and security schemes.
    """
    spec = _validate_spec_source(spec)
    override_path = _resolve_override(spec, override, no_override)
    try:
        parser = OpenApiParser(spec, override=override_path)
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
    override: Path | None = typer.Option(None, "--override", help=OVERRIDE_HELP),
    no_override: bool = typer.Option(False, "--no-override", help=NO_OVERRIDE_HELP),
) -> None:
    """
    Validate an OpenAPI spec without generating any files.

    Checks that the spec is valid YAML/JSON and conforms to OpenAPI 3.x schema.
    Returns exit code 0 on success, 1 on failure.
    """
    spec = _validate_spec_source(spec)
    override_path = _resolve_override(spec, override, no_override)
    errors: list[str] = []

    try:
        parser = OpenApiParser(spec, override=override_path)
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
    override: Path | None = typer.Option(None, "--override", help=OVERRIDE_HELP),
    no_override: bool = typer.Option(False, "--no-override", help=NO_OVERRIDE_HELP),
) -> None:
    """
    List all paths in the spec, optionally filtered by HTTP methods.
    """
    spec = _validate_spec_source(spec)
    override_path = _resolve_override(spec, override, no_override)
    methods = _method_upper_list(method)
    try:
        parser = OpenApiParser(spec, override=override_path)
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
    override: Path | None = typer.Option(None, "--override", help=OVERRIDE_HELP),
    no_override: bool = typer.Option(False, "--no-override", help=NO_OVERRIDE_HELP),
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
    override_path = _resolve_override(spec, override, no_override)
    try:
        parser = OpenApiParser(spec, override=override_path)
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
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Editor mode: default, kulala, pycharm, or httpyac.",
        show_default="default",
    ),
    include_examples: bool | None = typer.Option(
        None,
        "--include-examples/--no-include-examples",
        help="Include commented response examples next to each request.",
        show_default="no-include-examples",
    ),
    include_schema: bool | None = typer.Option(
        None,
        "--include-schema/--no-include-schema",
        help="Include commented request body examples next to each request.",
        show_default="no-include-schema",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite/--no-overwrite",
        help="Overwrite existing .http outputs. Existing env files are always merged.",
    ),
    env: bool = typer.Option(
        True, "--env/--no-env", help="Also generate env files for each spec."
    ),
    env_name: str | None = typer.Option(
        None, "--env-name", help="Environment section name.", show_default="dev"
    ),
    no_override: bool = typer.Option(
        False, "--no-override", help="Ignore <spec>_override.* files next to specs."
    ),
) -> None:
    """
    Process a directory of OpenAPI specs (or a single file) and generate .http (+ env) for each.
    """
    mode, filemode, base_url, env_name, include_examples, include_schema = (
        _apply_config_defaults(
            mode, filemode, base_url, env_name, include_examples, include_schema
        )
    )
    processed = 0
    failures: list[dict[str, str]] = []

    files: list[Path] = []
    if input_path.is_file():
        files = [input_path]
    elif input_path.is_dir():
        pats = [p.strip() for p in pattern.split(",") if p.strip()]
        for pat in pats:
            files.extend(input_path.glob(pat))
        files = sorted(f for f in set(files) if not is_override_file(f))
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
            override_path = None if no_override else find_override(spec)
            if override_path is not None:
                typer.secho(f"Using override: {override_path}", fg=typer.colors.CYAN)
            gen = HtttpFileGenerator(spec, settings=settings, override=override_path)
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
                _write_env_files(gen, public_env, private_env, env_name)
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


@override_app.command("oauth2")
def override_oauth2(
    spec: Path = typer.Argument(..., help="Path to the OpenAPI spec (yaml/json)."),
    token_url: str = typer.Option(
        PLACEHOLDER_TOKEN_URL, "--token-url", help="OAuth2 token endpoint."
    ),
    scope: list[str] | None = typer.Option(
        None, "--scope", help="OAuth2 scope; can be passed multiple times."
    ),
    out: Path | None = typer.Option(
        None,
        "--out",
        "-o",
        help="Override file path. Defaults to <spec>_override.<ext> next to the spec.",
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite/--no-overwrite", help="Overwrite an existing override."
    ),
    add: bool = typer.Option(
        False,
        "--add",
        help="Add a new OAuth2 scheme and require it for every operation without "
        "its own security, instead of converting bearer schemes.",
    ),
    scheme_name: str = typer.Option(
        DEFAULT_ADDED_SCHEME, "--scheme-name", help="Name of the scheme added by --add."
    ),
) -> None:
    """
    Write an override that switches the spec to OAuth2 client credentials.

    By default HTTP bearer schemes are converted; with --add a new scheme is added.
    """
    _validate_spec_source(spec)
    try:
        data = load_document(spec)
    except Exception as e:
        _abort(f"Failed to read spec: {e}")
    if add:
        try:
            patch = add_oauth2_patch(
                data, name=scheme_name, token_url=token_url, scopes=scope
            )
        except ValueError as e:
            _abort(str(e))
    else:
        patch = bearer_to_oauth2_patch(data, token_url=token_url, scopes=scope)
        if not patch:
            _abort(
                "No HTTP bearer security schemes found in the spec. "
                "Use --add to add an OAuth2 scheme instead."
            )
    out_path = out or default_override_path(spec)
    _ensure_write_target(out_path, overwrite)
    out_path.write_text(dump_document(patch, out_path))

    schemes = ", ".join(patch["components"]["securitySchemes"])
    typer.secho(f"Override written: {out_path}", fg=typer.colors.GREEN)
    if add:
        typer.echo(f"  Added OAuth2 client credentials scheme: {schemes}")
    else:
        typer.echo(f"  Converted to OAuth2 client credentials: {schemes}")
    if token_url == PLACEHOLDER_TOKEN_URL:
        typer.secho(
            "  Token URL is a placeholder; pass --token-url or edit the override.",
            fg=typer.colors.YELLOW,
        )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
