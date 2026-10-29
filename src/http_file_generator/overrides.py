"""Spec override files: JSON Merge Patch (RFC 7386) documents applied to a spec.

An override for ``api.json`` lives next to it as ``api_override.json`` (or
``.yaml``/``.yml``) and is applied automatically before the spec is resolved.
"""

import json
from pathlib import Path
from typing import Any

OVERRIDE_SUFFIX = "_override"
OVERRIDE_EXTENSIONS = (".yaml", ".yml", ".json")
PLACEHOLDER_TOKEN_URL = "https://CHANGE-ME.example.com/oauth2/token"


def is_override_file(path: Path) -> bool:
    return path.stem.endswith(OVERRIDE_SUFFIX) and path.suffix in OVERRIDE_EXTENSIONS


def default_override_path(spec: Path) -> Path:
    """Path a new override for ``spec`` is written to, matching the spec's format."""
    suffix = spec.suffix if spec.suffix in OVERRIDE_EXTENSIONS else ".yaml"
    return spec.with_name(f"{spec.stem}{OVERRIDE_SUFFIX}{suffix}")


def find_override(spec: Path) -> Path | None:
    """Return the first existing ``<stem>_override.{yaml,yml,json}`` next to ``spec``."""
    for ext in OVERRIDE_EXTENSIONS:
        candidate = spec.with_name(f"{spec.stem}{OVERRIDE_SUFFIX}{ext}")
        if candidate.is_file():
            return candidate
    return None


def merge_patch(target: Any, patch: Any) -> Any:
    """Apply an RFC 7386 JSON Merge Patch; ``None`` values delete keys."""
    if not isinstance(patch, dict):
        return patch
    result = dict(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = merge_patch(result.get(key), value)
    return result


def _parse(content: str) -> Any:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        import yaml

        return yaml.safe_load(content)


def load_document(path: Path) -> Any:
    return _parse(path.read_text())


def apply_override(data: Any, override: Path) -> Any:
    patch = load_document(override)
    if not isinstance(patch, dict):
        raise ValueError(f"Override must be a mapping: {override}")
    return merge_patch(data, patch)


def bearer_to_oauth2_patch(
    spec_data: dict[str, Any],
    token_url: str = PLACEHOLDER_TOKEN_URL,
    scopes: list[str] | None = None,
) -> dict[str, Any]:
    """Build a patch turning every HTTP bearer scheme into OAuth2 client credentials.

    Scheme names are kept, so existing ``security`` requirements still match.
    """
    schemes = (spec_data.get("components") or {}).get("securitySchemes") or {}
    patched: dict[str, Any] = {}
    for name, scheme in schemes.items():
        if not isinstance(scheme, dict):
            continue
        if (
            scheme.get("type") != "http"
            or str(scheme.get("scheme", "")).lower() != "bearer"
        ):
            continue
        patched[name] = {
            "type": "oauth2",
            "scheme": None,
            "bearerFormat": None,
            "flows": {
                "clientCredentials": {
                    "tokenUrl": token_url,
                    "scopes": {s: "" for s in scopes or []},
                }
            },
        }
    if not patched:
        return {}
    return {"components": {"securitySchemes": patched}}


def dump_document(data: Any, path: Path) -> str:
    if path.suffix == ".json":
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    import yaml

    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
