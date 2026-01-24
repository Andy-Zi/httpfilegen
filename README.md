# httpfilegen

A CLI tool to generate .http files and Kulala-compatible environment files from OpenAPI specs.

## Features

- Generate HTTP request collections (.http) from OpenAPI 3.x specs
- Generate http-client.env.json and http-client.private.env.json skeletons from security schemes
- Inspect specs: summary, paths, and request/response samples
- Batch process directories of spec files

## Tool Compatibility

Generated `.http` files and environment files work with:

- ✅ **Kulala (Neovim)**: Full support including environment files and BASE_URL management
- ✅ **PyCharm/IntelliJ IDEA**: Full support with JetBrains HTTP Client
- ✅ **httpyac (VS Code)**: Full support - use the httpyac extension for complete environment file support
- ⚠️ **VS Code REST Client**: Limited support - environment variables need manual setup in `.vscode/settings.json`

**Note**: BASE_URL is now managed per-environment in the `http-client.env.json` files instead of shared blocks in the HTTP files.

## Installation

Requires Python 3.13+

### Standard Installation

```bash
# From the project root (pick one)
pip install -e .
# or using uv
uv pip install -e .
```

This will install the `httpfilegen` command.

### NixOS/Home Manager Installation

If you're using NixOS with Home Manager, you can use the provided flake:

```nix
# In your home.nix
{
  imports = [
    # Import the httpfilegen Home Manager module
    inputs.httpfilegen.homeManagerModules.httpfilegen
  ];

  programs.httpfilegen = {
    enable = true;

    # Configure default CLI options (optional)
    defaults = {
      mode = "default";  # or "kulala", "pycharm", "vscode"
      filemode = "single";
      baseUrl = "https://api.example.com";
      envName = "dev";
      includeExamples = true;
      includeSchema = false;
    };
  };
}
```

Then enter the development shell:
```bash
cd /path/to/httpfilegen
nix develop
```

Or install the package system-wide:
```bash
nix build
nix profile install ./result
```

The Home Manager module creates a config file at `~/.config/httpfilegen/config.toml` with your configured defaults (see Configuration section above).

## Usage

```bash
httpfilegen --help
```

## Configuration

httpfilegen supports configuration files for setting default CLI options. The config file is located at `~/.config/httpfilegen/config.toml`.

### Config File Format

Create or edit `~/.config/httpfilegen/config.toml`:

```toml
# Editor mode for optimized behavior
# Options: default, kulala, pycharm, vscode
mode = "default"

# Default file generation mode
# Options: single, multi
filemode = "single"

# Default base URL for generated files
base_url = "https://api.example.com"

# Default environment name
env_name = "dev"

# Default include options
include_examples = false
include_schema = false
```

### How It Works

- CLI arguments always take precedence over config file defaults
- Only non-provided CLI options will use config defaults
- Config file is optional - httpfilegen works without it
- Invalid config files are ignored with a warning

### Example Usage

With the above config, this command:
```bash
httpfilegen generate spec.yaml
```

Is equivalent to:
```bash
httpfilegen generate spec.yaml --mode default --filemode single --base-url https://api.example.com --env-name dev
```

But you can still override any option:
```bash
httpfilegen generate spec.yaml --filemode multi --include-examples
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
- `--base-url`: Optional base URL to include in environment files. This creates an additional environment alongside any servers defined in the spec.
- `--include-examples/--no-include-examples`: Include commented response examples next to each request.
- `--include-schema/--no-include-schema`: Include commented request body examples (based on provided examples or schema fallback) next to each request.
- `--dry-run`: Preview output without writing any files. Shows what would be generated.

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

### Validate a spec

Validate an OpenAPI spec without generating any files:

```bash
httpfilegen validate path/to/openapi.yaml
```

For CI/CD pipelines, use JSON output:

```bash
httpfilegen validate path/to/openapi.yaml --json
```

Returns exit code 0 on success, 1 on failure.

### Preview output (dry run)

Preview what would be generated without writing any files:

```bash
httpfilegen generate path/to/openapi.yaml --dry-run
```

This shows the first 100 lines of the generated .http file and lists any env files that would be created.

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
from pydantic_core import Url
settings = HttpSettings(filemode=Filemode.SINGLE, baseURL=Url("https://api.example.com"), include_examples=True, include_schema=True)
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
- When using `--base-url` or `HttpSettings.baseURL`, the URL creates an additional environment in the generated env files. If the spec also defines servers, each server creates its own environment.
- In `MULTI` mode, env files (if enabled) default to being written next to the generated tree unless `--env-dir` is specified.

## Generated Output Examples

### Sample .http File

```http
# JetBrains HTTP Client file
# https://www.jetbrains.com/help/idea/http-client-in-product-code-editor.html
# Supports: {{variable}}, # @name, pre/post scripts, http-client.env.json

@BASE_URL=https://api.example.com

### Get all users
# @name getUsers
GET {{BASE_URL}}/users
Accept: application/json

### Create a user
# @name createUser
< {% request.variables.set('timestamp', Date.now()); %}
POST {{BASE_URL}}/users
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com"
}

> {% client.assert(response.status === 201); %}

### Get user by ID
# @name getUserById
GET {{BASE_URL}}/users/{{userId}}
Accept: application/json
Authorization: Bearer {{auth_token}}
```

### Sample http-client.env.json

```json
{
  "dev": {
    "BASE_URL": "https://api.example.com",
    "userId": "123"
  },
  "staging": {
    "BASE_URL": "https://staging.api.example.com",
    "userId": "456"
  }
}
```

### Sample http-client.private.env.json

```json
{
  "dev": {
    "auth_token": "",
    "api_key": ""
  },
  "staging": {
    "auth_token": "",
    "api_key": ""
  }
}
```

## Troubleshooting

### Common Errors

#### "Failed to parse spec content"

**Symptoms:** Error message showing both JSON and YAML parse failures.

**Cause:** The OpenAPI spec file contains syntax errors.

**Solution:**
1. Validate your spec with an online tool like [Swagger Editor](https://editor.swagger.io/)
2. Check for common YAML issues: incorrect indentation, missing colons, unquoted special characters
3. For JSON, ensure proper comma placement and balanced braces

#### "OpenAPI validation error"

**Symptoms:** Error mentioning missing required fields or invalid OpenAPI structure.

**Cause:** The spec is valid YAML/JSON but doesn't conform to OpenAPI 3.x schema.

**Solution:**
1. Ensure `openapi: "3.0.0"` (or 3.1.x) is present at the root
2. Verify required fields: `info.title`, `info.version`, `paths`
3. Check that all `$ref` references point to valid definitions

#### "FileNotFoundError" or "No such file"

**Symptoms:** The specified spec file cannot be found.

**Solution:**
1. Check the file path is correct (use absolute paths if unsure)
2. Verify file extension matches (`.yaml`, `.yml`, or `.json`)
3. For URLs, ensure the spec is publicly accessible

#### "HTTP Error" when loading remote spec

**Symptoms:** Error fetching spec from URL (401, 403, 404, etc.)

**Solution:**
1. **401/403**: The spec requires authentication; download it locally first
2. **404**: Verify the URL is correct and the spec exists
3. **Timeout**: Check network connectivity; try downloading manually

#### Missing environment variables in output

**Symptoms:** Generated .http file uses `{{variable}}` but env files don't define them.

**Solution:**
1. Security scheme variables (API keys, tokens) go in `http-client.private.env.json`
2. Use `--base-url` to set a custom BASE_URL
3. Path parameters like `{{userId}}` must be manually added to env files

### FAQ

**Q: Why are my pre/post request scripts not appearing?**

A: Scripts are extracted from OpenAPI `x-pre-request-script` and `x-post-request-script` extensions on operations. Add these to your spec:

```yaml
paths:
  /users:
    get:
      x-pre-request-script: "console.log('before');"
      x-post-request-script: "client.assert(response.status === 200);"
```

**Q: How do I switch between environments?**

A: In your editor:
- **Kulala/PyCharm**: Select environment from the dropdown or run menu
- **httpyac**: Use `# @env dev` directive or VS Code command palette
- **VS Code REST Client**: Define environments in `.vscode/settings.json`

**Q: Why use `--mode` flag?**

A: The `--mode` flag adds editor-specific header comments for better IDE integration:
- `--mode pycharm`: JetBrains documentation link
- `--mode kulala`: Kulala.nvim documentation link
- `--mode httpyac`: httpyac documentation link
- `--mode default`: No header (maximum compatibility)

The actual request syntax is identical across all modes.

## Development

- Install dev dependencies: `uv pip install -e ".[test]"`
- Run tests: `uv run pytest`
- Run with coverage: `uv run pytest --cov=src --cov-report=term-missing`
- Lint: `uv run ruff check src/ tests/`
- Format: `uv run ruff format src/ tests/`
- Code lives under `src/` using a src-layout.

## License

MIT
