"""Load an OpenAPI spec from a file or URL, apply its override and resolve $refs."""

import json
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from prance import ResolvingParser, ValidationError

from .overrides import apply_override


def _parse_spec_content(content: str) -> Any:
    """Parse content as JSON first, then try YAML if JSON fails."""
    json_error = None
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        json_error = e

    # JSON failed, try YAML
    try:
        import yaml

        return yaml.safe_load(content)
    except ImportError:
        raise ValueError(
            "YAML support not available. Install PyYAML: pip install pyyaml"
        )
    except yaml.YAMLError as e:
        raise ValueError(
            f"Failed to parse spec content.\n"
            f"  JSON error: {json_error}\n"
            f"  YAML error: {e}"
        )
    except Exception as e:
        raise ValueError(f"Failed to parse spec content: {e}")


def load_data(file: Path | str, override: Path | None = None) -> Any:
    if isinstance(file, Path):
        content = Path(file).read_text()
        data = _parse_spec_content(content)
    else:
        parsed = urlparse(file)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            try:
                with urllib.request.urlopen(file, timeout=30) as resp:
                    charset = resp.headers.get_content_charset() or "utf-8"
                    content = resp.read().decode(charset)
                data = _parse_spec_content(content)
            except urllib.error.HTTPError as e:
                raise ValueError(
                    f"HTTP error fetching spec from '{file}': {e.code} {e.reason}"
                )
            except urllib.error.URLError as e:
                raise ValueError(
                    f"Network error fetching spec from '{file}': {e.reason}"
                )
            except TimeoutError:
                raise ValueError(
                    f"Timeout fetching spec from '{file}' (30s limit exceeded)"
                )
            except Exception as e:
                raise ValueError(f"Failed to fetch spec from '{file}': {e}")
        else:
            # Treat as a local file path string
            content = Path(file).read_text()
            data = _parse_spec_content(content)

    if override is not None:
        data = apply_override(data, override)

    def _recursion_handler(limit, ref_url, recursions):
        return {}

    try:
        return ResolvingParser(
            spec_string=json.dumps(data),
            recursion_limit_handler=_recursion_handler,
        ).specification
    except ValidationError as e:
        # Try to recover from OpenAPI 3.1+ validation issues
        openapi_version = data.get("openapi", "unknown")
        try:
            major, minor, patch = str(openapi_version).split(".")
            if int(major) == 3 and (int(minor) > 0 or int(patch) > 0):
                data["openapi"] = "3.1.0"
                return ResolvingParser(
                    spec_string=json.dumps(data),
                    recursion_limit_handler=_recursion_handler,
                ).specification
        except (ValueError, AttributeError):
            pass
        raise ValueError(f"OpenAPI validation failed (version: {openapi_version}): {e}")
