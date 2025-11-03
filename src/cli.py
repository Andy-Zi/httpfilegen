import typer
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from http_file_generator import HtttpFileGenerator
from http_file_generator.models import OpenApiParser, METHOD, HttpSettings, Filemode

app = typer.Typer(
    help="Generate .http files and env files from an OpenAPI spec.",
    no_args_is_help=True,
    add_completion=False,
)


def _abort(msg: str, code: int = 1):
    typer.secho(msg, fg=typer.colors.RED, err=True)
    raise typer.Exit(code)


def _json_print(data: Any):
    typer.echo(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _is_url(s: str | Path) -> bool:
    if isinstance(s, Path):
        return False
    return s.startswith("http://") or s.startswith("https://")


def _validate_spec_source(spec: str | Path) -> str | Path:
    if _is_url(spec):
        return spec
    p = spec if isinstance(spec, Path) else Path(spec)
    if not p.exists() or not p.is_file():
        _abort(f"Spec file not found: {spec}")
    return p


def _ensure_write_target(path: Path, overwrite: bool):
    if path.exists() and not overwrite:
        _abort(f"Refusing to overwrite existing file without --overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)


def _method_upper_list(methods: Optional[List[str]]) -> Optional[List[str]]:
    if methods is None:
        return None
    result: List[str] = []
    for m in methods:
        mu = m.upper()
        if mu not in METHOD.__members__.keys() and mu not in {e.value for e in METHOD}:
            _abort(f"Unknown method: {m}")
        result.append(mu)
    return result


def _parse_filemode(value: Optional[str]) -> Filemode:
    if value is None:
        return Filemode.SINGLE
    v = value.strip().lower()
    if v in ("single", "s"):
        return Filemode.SINGLE
    if v in ("multi", "m"):
        return Filemode.MULTI
    _abort("Invalid value for --filemode: choose 'single' or 'multi'.")


@app.command("generate")
def generate(
    spec: str = typer.Argument(
        ..., help="Path or URL to the OpenAPI spec (yaml/json)."
    ),
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Output .http file path. Defaults to <spec>.http next to the spec.",
    ),
    filemode: Optional[str] = typer.Option(
        None,
        "--filemode",
        "-f",
        help="File generation mode: SINGLE (one .http) or MULTI (one per path).",
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="Optional base URL to include in generated .http files.",
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
    env_dir: Optional[Path] = typer.Option(
        None,
        "--env-dir",
        help="Directory where env files will be written. Defaults to the .http file directory.",
    ),
    public_env_filename: str = typer.Option(
        "http-client.env.json", "--public-env-filename", help="Public env filename."
    ),
    private_env_filename: str = typer.Option(
        "http-client.private.env.json",
        "--private-env-filename",
        help="Private env filename.",
    ),
):
    """
    Generate a .http file from an OpenAPI spec.
    Optionally also generate http-client env files.
    """
    spec = _validate_spec_source(spec)
    # Derive output path (file or directory depending on filemode)
    if out is not None:
        out_path = out
    else:
        if _is_url(spec):
            # derive name from URL path segment
            name = Path(str(spec).rstrip("/").split("/")[-1]).stem or "openapi"
            out_path = Path.cwd() / f"{name}.http"
        else:
            out_path = Path(spec).with_suffix(".http")

    try:
        fm = _parse_filemode(filemode)
        settings = HttpSettings(
            filemode=fm,
            baseURL=base_url,
            include_examples=include_examples,
            include_schema=include_schema,
        )
        gen = HtttpFileGenerator(spec, settings=settings)
    except Exception as e:
        _abort(f"Failed to parse spec: {e}")

    # Ensure write target based on mode
    if fm == Filemode.SINGLE:
        _ensure_write_target(out_path, overwrite)
        try:
            gen.to_http_file(out_path)
        except Exception as e:
            _abort(f"Failed to write HTTP file: {e}")
        typer.secho(f"HTTP file generated: {out_path}", fg=typer.colors.GREEN)
        default_env_dir = out_path.parent
    else:
        # MULTI mode: resolve target directory
        target_dir = out_path.parent / out_path.stem if out_path.suffix == ".http" else out_path
        if target_dir.exists() and not overwrite:
            _abort(f"Refusing to overwrite existing directory without --overwrite: {target_dir}")
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            gen.to_http_file(target_dir)
        except Exception as e:
            _abort(f"Failed to write HTTP files: {e}")
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
            gen.to_env_files(public_env, private_env, env_name=env_name)
        except Exception as e:
            _abort(f"Failed to write env files: {e}")
        typer.secho(
            f"Env files generated: {public_env}, {private_env}", fg=typer.colors.GREEN
        )


@app.command("env")
def gen_env(
    spec: str = typer.Argument(
        ..., help="Path or URL to the OpenAPI spec (yaml/json)."
    ),
    out_dir: Optional[Path] = typer.Option(
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
):
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
        gen.to_env_files(public_env, private_env, env_name=env_name)
    except Exception as e:
        _abort(f"Failed to write env files: {e}")
    typer.secho(
        f"Env files generated: {public_env}, {private_env}", fg=typer.colors.GREEN
    )


@app.command("info")
def info(
    spec: str = typer.Argument(
        ..., help="Path or URL to the OpenAPI spec (yaml/json)."
    ),
    json_out: bool = typer.Option(False, "--json", help="Output as JSON."),
):
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
    method_counts: Dict[str, int] = {}
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


@app.command("paths")
def list_paths(
    spec: str = typer.Argument(
        ..., help="Path or URL to the OpenAPI spec (yaml/json)."
    ),
    method: Optional[List[str]] = typer.Option(
        None,
        "--method",
        "-m",
        help="Filter by HTTP method; can be passed multiple times.",
    ),
    with_methods: bool = typer.Option(
        True, "--with-methods/--no-with-methods", help="Show methods next to each path."
    ),
):
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
    spec: str = typer.Argument(..., help="Path or URL to the OpenAPI spec (yaml/json)."),
    path: str = typer.Argument(..., help="The API path to inspect, e.g. /users/{id}."),
    method: Optional[str] = typer.Option(
        None, "--method", "-m", help="HTTP method to show. Defaults to all."
    ),
    request: bool = typer.Option(
        True, "--request/--no-request", help="Include request body samples."
    ),
    response: bool = typer.Option(
        True, "--response/--no-response", help="Include response body samples."
    ),
    status: Optional[str] = typer.Option(
        None, "--status", help="Filter a specific response HTTP status."
    ),
    content_type: Optional[str] = typer.Option(
        None, "--content-type", help="Filter a specific content type."
    ),
):
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

    result: Dict[str, Any] = {"path": path}
    if request:
        reqs = parser.get_request_body(path)
        if m_upper:
            reqs = {m_upper: reqs.get(m_upper)}
        if content_type:
            filt: Dict[str, Any] = {}
            for m, body in reqs.items():
                if not body:
                    filt[m] = None
                else:
                    if content_type in body:
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
            filt_resp: Dict[str, Any] = {}
            for m, bodies in resps.items():
                if not bodies:
                    filt_resp[m] = {}
                    continue
                new_status_map: Dict[str, Any] = {}
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
    filemode: Optional[str] = typer.Option(
        None,
        "--filemode",
        "-f",
        help="File generation mode: SINGLE (one .http) or MULTI (one per path).",
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="Optional base URL to include in generated .http files.",
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
):
    """
    Process a directory of OpenAPI specs (or a single file) and generate .http (+ env) for each.
    """
    processed = 0
    failures: List[Dict[str, str]] = []

    files: List[Path] = []
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
            settings = HttpSettings(
                filemode=fm,
                baseURL=base_url,
                include_examples=include_examples,
                include_schema=include_schema,
            )
            gen = HtttpFileGenerator(spec, settings=settings)
            if fm == Filemode.SINGLE:
                out_file = spec.with_suffix(".http")
                _ensure_write_target(out_file, overwrite)
                content = gen.http_file.to_http_file(
                    include_examples=settings.include_examples,
                    include_schema=settings.include_schema,
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
                typer.secho(f"Generated (MULTI): {spec} -> {env_base_dir}", fg=typer.colors.GREEN)
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


def main():
    app()


if __name__ == "__main__":
    main()
