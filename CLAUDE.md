# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

httpfilegen is a Python CLI tool that generates `.http` files (HTTP request collections) and environment configuration files from OpenAPI 3.x specifications. It supports multiple output formats for Kulala/Neovim, PyCharm/IntelliJ, and httpyac/VS Code.

## Essential Commands

```bash
# Setup
uv sync --extra test

# Run tests
uv run pytest                                    # All tests
uv run pytest tests/test_file.py::test_name     # Single test
uv run pytest -k "pattern"                       # Tests matching pattern

# Lint and format
uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/

# Coverage (80% threshold enforced)
uv run coverage report --fail-under=80
```

## Architecture

**src-layout with CLI entry point:**
- `src/cli.py` - Typer CLI commands (generate, env, info, paths, sample, batch)
- `src/http_file_generator/` - Core package
  - `http_file_generator.py` - Main `HtttpFileGenerator` class (note: typo in name is intentional)
  - `models/` - Pydantic data models
    - `http_file/` - OpenAPI parsing (`open_api_parser.py`), HTTP request models
    - `env_file/` - Environment file generation
    - `settings/` - `HttpSettings`, `Filemode` enums
    - `utils/` - Parameter, body, and auth parsing helpers

**Key patterns:**
- OpenAPI specs parsed via `prance` (resolves external $refs) + `openapi-pydantic`
- `Filemode.SINGLE` creates one .http file; `Filemode.MULTI` creates per-path directory tree
- Environment files: `http-client.env.json` (public) + `http-client.private.env.json` (secrets)

## Development Guidelines

See `AGENTS.md` for comprehensive code style, patterns, and conventions. Key points:

- Python 3.13+ required
- Use `Union[X, None]` not `Optional[X]` (Typer compatibility)
- Use `Union[X, Y]` not `X | Y` (Typer doesn't support modern union syntax)
- Use `pathlib.Path` exclusively for file operations
- CLI errors: use `_abort()` helper with colored output
- Tests: pytest with `CliRunner`, use `tmp_path` fixture for temp files
