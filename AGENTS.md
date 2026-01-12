# AGENTS.md - Development Guidelines for httpfilegen

This file contains development guidelines and commands for coding agents working on the httpfilegen project.

## Build/Lint/Test Commands

### Testing
- **Run all tests**: `uv run pytest`
- **Run tests with coverage**: `uv run pytest` (coverage is configured in pyproject.toml)
- **Run a single test file**: `uv run pytest tests/test_filename.py`
- **Run a single test function**: `uv run pytest tests/test_filename.py::test_function_name`
- **Run tests matching pattern**: `uv run pytest -k "pattern"`
- **Run tests and exit on first failure**: `uv run pytest -x`
- **Run tests in verbose mode**: `uv run pytest -v`

### Linting and Code Quality
- **Install ruff** (if not already installed): `uv add --dev ruff`
- **Lint code**: `uv run ruff check src/ tests/`
- **Auto-fix linting issues**: `uv run ruff check --fix src/ tests/`
- **Format code**: `uv run ruff format src/ tests/`
- **Check and format**: `uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/`

### Building and Installation
- **Install in development mode**: `uv pip install -e .`
- **Build distribution**: `python -m build` or `uv build`
- **Install test dependencies**: `uv sync --extra test`

### Coverage
- **Check coverage threshold** (80%): `uv run coverage report --fail-under=80`
- **Generate HTML coverage report**: `uv run coverage html`

## Code Style Guidelines

### Python Version and Imports
- **Python version**: 3.13+ required
- **Import order**:
  ```python
  import json
  from pathlib import Path
  from typing import Any, NoReturn

  import typer

  from http_file_generator import HtttpFileGenerator
  from http_file_generator.models import METHOD, Filemode, HttpSettings, OpenApiParser
  ```
- **Import style**: Use absolute imports for internal modules
- **Avoid star imports**: `from module import *` is not used

### Type Hints
- **Use type hints extensively**: All function parameters and return values should be typed
- **Common types**: Use `typing.Any`, `typing.NoReturn`, `pathlib.Path`, etc.
- **Optional types**: Use `X | None` instead of `Optional[X]` (Python 3.10+ union syntax)
- **Generic types**: Use `list[str]` instead of `List[str]`

### Naming Conventions
- **Functions and variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Enums**: `UPPER_CASE` for values (following StrEnum pattern)
- **Private members**: Prefix with single underscore `_`
- **Modules**: `snake_case` with underscores

### Code Structure
- **Project layout**: src-layout with main package in `src/http_file_generator/`
- **Entry points**: CLI commands defined in `src/cli.py`
- **Models**: Data classes and enums in `src/http_file_generator/models/`
- **Utilities**: Helper functions in `src/http_file_generator/models/utils/`

### Error Handling
- **CLI errors**: Use `typer.secho()` with `typer.colors.RED` and `raise typer.Exit(code)`
- **Exceptions**: Use try/except blocks, re-raise with context when appropriate
- **Validation**: Validate inputs early, use descriptive error messages
- **Path validation**: Check file existence and permissions before operations

### Documentation
- **Docstrings**: Use triple quotes for module/class/function documentation
- **CLI help**: Comprehensive help text for typer commands
- **Comments**: Minimal comments, prefer self-documenting code
- **Type hints**: Serve as documentation for parameters and return values

### File Operations
- **Path handling**: Use `pathlib.Path` exclusively
- **File creation**: Check parent directories exist, use `parents=True` in `mkdir()`
- **Overwrite protection**: Check for existing files unless `--overwrite` is specified
- **Atomic writes**: Write to temporary files then move, or use context managers

### CLI Design
- **Command structure**: Use typer with subcommands
- **Options**: Use descriptive long names with short aliases
- **Defaults**: Sensible defaults, override with flags
- **Output**: Use `typer.echo()` for normal output, `typer.secho()` for colored/styled output
- **Exit codes**: 0 for success, 1 for errors

### Testing
- **Test framework**: pytest with standard assertions
- **Test naming**: `test_descriptive_name`
- **Test structure**: Arrange-Act-Assert pattern
- **Fixtures**: Use pytest fixtures for setup/teardown
- **CLI testing**: Use `typer.testing.CliRunner`
- **Temp files**: Use `tmp_path` fixture for temporary file operations
- **Coverage**: Aim for high coverage, especially on new code

### Dependencies
- **Management**: Use uv for dependency management
- **Specification**: Dependencies in `pyproject.toml`
- **Optional deps**: Test dependencies in `[project.optional-dependencies]`
- **Lock file**: `uv.lock` for reproducible installs

### Git Workflow
- **Commits**: Descriptive commit messages following conventional format
- **Branching**: Feature branches for development
- **CI/CD**: GitHub Actions workflow runs tests on push/PR
- **Coverage**: Must maintain 80% coverage threshold

### Security
- **Secrets**: Never commit secrets, API keys, or credentials
- **Input validation**: Validate all user inputs, especially file paths and URLs
- **File operations**: Safe file handling with proper permissions
- **Network**: Use HTTPS URLs, validate SSL certificates

### Performance
- **Efficiency**: Use appropriate data structures (dicts for lookups, lists for sequences)
- **Memory**: Process large files/streaming when possible
- **Caching**: Cache expensive operations when beneficial
- **Async**: Consider async for I/O operations if needed

## Development Workflow

1. **Setup**: `uv sync --extra test && uv pip install -e .`
2. **Code**: Make changes following style guidelines
3. **Test**: `uv run pytest` to run tests
4. **Lint**: `uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/`
5. **Coverage**: Ensure coverage remains above 80%
6. **Commit**: Write descriptive commit messages

## Common Patterns

### CLI Command Structure
```python
@app.command("command_name")
def command_name(
    param: str = typer.Argument(..., help="Description"),
    option: bool = typer.Option(False, "--option/--no-option", help="Description"),
) -> None:
    """Command description."""
    try:
        # Implementation
        typer.secho("Success message", fg=typer.colors.GREEN)
    except Exception as e:
        _abort(f"Error message: {e}")
```

### Error Handling
```python
def _abort(msg: str, code: int = 1) -> NoReturn:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    raise typer.Exit(code)

try:
    # Risky operation
except Exception as e:
    _abort(f"Operation failed: {e}")
```

### File Operations
```python
def safe_write_file(path: Path, content: str, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        _abort(f"File exists, use --overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
```

### Type Hints Example
```python
from typing import Any, NoReturn
from pathlib import Path

def process_spec(spec: str | Path, settings: dict[str, Any]) -> dict[str, Any]:
    """Process an OpenAPI spec and return results."""
    # Implementation
    pass
```</content>
<parameter name="filePath">/home/az/Code/httpfilegen/AGENTS.md