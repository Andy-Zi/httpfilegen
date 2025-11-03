# httpfilegen

A CLI tool to generate .http files and Kulala-compatible environment files from OpenAPI specs.

## Features

- Generate HTTP request collections (.http) from OpenAPI 3.x specs
- Generate http-client.env.json and http-client.private.env.json skeletons from security schemes
- Inspect specs: summary, paths, and request/response samples
- Batch process directories of spec files

## Installation

Requires Python 3.13+

```bash
# From the project root (pick one)
pip install -e .
# or using uv
uv pip install -e .
```

This will install the `httpfilegen` command.

## Usage

```bash
httpfilegen --help
```

### Generate a .http file (and env files)

```bash
httpfilegen generate path/to/openapi.yaml \
  --out path/to/output.http \
  --env-name dev \
  --overwrite
```

- By default, an output file is created next to the spec with the same basename and .http extension.
- Add `--no-env` to skip environment files.

Options of interest:
- `--filemode, -f`: Generation mode. `SINGLE` (default) writes one .http file. `MULTI` writes one .http per API path and mirrors the path structure as directories.
- `--base-url`: Optional base URL to include in the generated .http file(s). This is added to the Shared section alongside any servers defined in the spec.
- `--include-examples/--no-include-examples`: Include commented response examples next to each request.
- `--include-schema/--no-include-schema`: Include commented request body examples (based on provided examples or schema fallback) next to each request.

Examples:

Single file with an explicit base URL:

```bash
httpfilegen generate path/to/openapi.yaml \
  --out api.http \
  --base-url https://api.example.com
```

Multi-file output (one per path) under a directory derived from the output name:

```bash
httpfilegen generate path/to/openapi.yaml \
  --out api.http \
  --filemode MULTI
# Creates ./api/<path-segments>/index.http
```

Multi-file with explicit base URL and env files under the same directory tree:

```bash
httpfilegen generate path/to/openapi.yaml \
  --out api.http \
  --filemode MULTI \
  --base-url https://api.example.com \
  --include-schema \
  --include-examples \
  --env
```

### Generate only env files

```bash
httpfilegen env path/to/openapi.yaml \
  --env-name dev \
  --out-dir ./
```

Environment files:
- `http-client.env.json` (public)
- `http-client.private.env.json` (secrets and variables)

### Inspect the spec

Basic info:

```bash
httpfilegen info path/to/openapi.yaml
```

List paths (optionally filter by method):

```bash
httpfilegen paths path/to/openapi.yaml --method get --method post
```

Show request/response samples for a specific path:

```bash
httpfilegen sample path/to/openapi.yaml \
  "/users/{id}" \
  --method get \
  --content-type application/json \
  --status 200
```

### Batch processing

```bash
httpfilegen batch path/to/specs \
  --pattern "*.json,*.yaml,*.yml" \
  --filemode MULTI \
  --base-url https://api.example.com \
  --env-name dev \
  --overwrite
```

This scans the directory for matching specs and generates `.http` (+ env files) for each.

## Programmatic usage

You can also import and use the generator in Python code:

````python
# filepath: examples/programmatic.py
from pathlib import Path
from http_file_generator import HtttpFileGenerator
from http_file_generator.models import HttpSettings, Filemode

spec = Path("path/to/openapi.yaml")
out = Path("path/to/output.http")

# Single file with optional base URL and response examples
settings = HttpSettings(filemode=Filemode.SINGLE, baseURL="https://api.example.com", include_examples=True, include_schema=True)
http_file_generator = HtttpFileGenerator(spec, settings=settings)
http_file_generator.to_http_file(out)

# Multi-file output under a directory mirroring API paths
# http_file_generator = HtttpFileGenerator(spec, settings=HttpSettings(filemode=Filemode.MULTI))
# http_file_generator.to_http_file(Path("api.http"))  # creates ./api/<segments>/index.http

# Optional env files
public_env = out.parent / "http-client.env.json"
private_env = out.parent / "http-client.private.env.json"
http_file_generator.to_env_files(public_env, private_env, env_name="dev")
````

## Notes

- Generated env files follow the schemas used by Kulala. Private env contains only secrets and extra variables; public env contains non-sensitive auth config.
- OpenAPI parsing relies on prance and openapi-pydantic; external $refs are resolved automatically.
- When using `--base-url` or `HttpSettings.baseURL`, the URL is included in the Shared section of every generated .http file. If the spec also defines servers, those will be listed as well.
- In `MULTI` mode, env files (if enabled) default to being written next to the generated tree unless `--env-dir` is specified.

## Development

- Install dev dependencies, run in editable mode, and execute CLI locally.
- Code lives under `src/` using a src-layout.

## License

MIT
