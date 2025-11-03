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
  --env-name dev \
  --overwrite
```

This scans the directory for matching specs and generates `.http` (+ env files) for each.

## Programmatic usage

You can also import and use the generator in Python code:

````python
# filepath: examples/programmatic.py
from pathlib import Path
from http_file_generator import HttttpFileGenerator

spec = Path("path/to/openapi.yaml")
out = Path("path/to/output.http")

http_file_generator = HttttpFileGenerator(spec)
http_file_generator.to_http_file(out)

# Optional env files
public_env = out.parent / "http-client.env.json"
private_env = out.parent / "http-client.private.env.json"
http_file_generator.to_env_files(public_env, private_env, env_name="dev")
````

## Notes

- Generated env files follow the schemas used by Kulala. Private env contains only secrets and extra variables; public env contains non-sensitive auth config.
- OpenAPI parsing relies on prance and openapi-pydantic; external $refs are resolved automatically.

## Development

- Install dev dependencies, run in editable mode, and execute CLI locally.
- Code lives under `src/` using a src-layout.

## License

MIT
