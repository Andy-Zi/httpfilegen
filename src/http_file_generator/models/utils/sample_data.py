"""Deterministic, plausible sample values for JSON schemas.

Spec-provided values win: ``const``, ``example``, ``examples``, ``default`` and
``enum`` are used as-is. Everything else is derived from the schema (``type``,
``format``, bounds, ``pattern``) and the property name, without randomness, so
regenerating a spec yields the same output. The only moving input is the
reference date for ``date``/``date-time`` values: today (UTC), or the day of
``SOURCE_DATE_EPOCH`` when that variable is set.
"""

import math
import os
import random
import re
import uuid
import zlib
from datetime import UTC, date, datetime, timedelta
from typing import Any

import rstr

_MAX_DEPTH = 10
_PATTERN_ATTEMPTS = 20

_END_TOKENS = {
    "end",
    "to",
    "until",
    "till",
    "expiry",
    "expires",
    "expiration",
    "stop",
    "finish",
}

_STATIC_FORMATS = {
    "time": ["00:00:00Z", "00:00:00", "00:00"],
    "duration": ["PT15M"],
    "email": ["user@example.com"],
    "idn-email": ["user@example.com"],
    "uri": ["https://example.com"],
    "url": ["https://example.com"],
    "iri": ["https://example.com"],
    "uri-reference": ["/example"],
    "iri-reference": ["/example"],
    "uri-template": ["https://example.com/{id}"],
    "hostname": ["example.com"],
    "idn-hostname": ["example.com"],
    "ipv4": ["192.0.2.1"],
    "ipv6": ["2001:db8::1"],
    "byte": ["ZXhhbXBsZQ=="],
    "binary": ["example"],
    "password": ["password"],
    "json-pointer": ["/example"],
    "regex": [".*"],
    "iso-4217": ["EUR"],
}


def reference_date() -> date:
    """Return the date used as anchor for generated dates."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        try:
            return datetime.fromtimestamp(int(epoch), UTC).date()
        except (ValueError, OverflowError, OSError):
            pass
    return datetime.now(UTC).date()


def generate_sample(schema: dict, today: date | None = None) -> Any:
    """Generate a sample value for ``schema``.

    Local ``$ref`` pointers are resolved against ``schema`` itself; unresolvable
    or recursive references yield ``None``. Raises ``ValueError`` for an
    unknown ``type``.
    """
    return _SampleGenerator(schema, today or reference_date()).sample(schema, "", 0)


def _name_tokens(name: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return [t.lower() for t in re.split(r"[^A-Za-z0-9]+", spaced) if t]


def _matches(value: str, schema: dict) -> bool:
    if "maxLength" in schema and len(value) > schema["maxLength"]:
        return False
    if "minLength" in schema and len(value) < schema["minLength"]:
        return False
    pattern = schema.get("pattern")
    if pattern:
        try:
            return re.search(pattern, value) is not None
        except re.error:
            return True
    return True


class _SampleGenerator:
    def __init__(self, root: dict, today: date) -> None:
        self.root = root
        self.today = today
        self.ref_stack: list[str] = []

    def resolve(self, ref: str) -> dict | None:
        if not ref.startswith("#"):
            return None
        node: Any = self.root
        for part in ref.lstrip("#").split("/"):
            if not part:
                continue
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node if isinstance(node, dict) else None

    def deref(self, schema: Any) -> dict | None:
        seen: set[str] = set()
        while isinstance(schema, dict) and "$ref" in schema:
            ref = schema["$ref"]
            if ref in seen or ref in self.ref_stack:
                return None
            seen.add(ref)
            schema = self.resolve(ref)
        return schema if isinstance(schema, dict) else None

    def sample(self, schema: Any, name: str, depth: int) -> Any:
        if not isinstance(schema, dict) or depth > _MAX_DEPTH:
            return None
        if "$ref" in schema:
            ref = schema["$ref"]
            target = self.deref(schema)
            if target is None:
                return None
            self.ref_stack.append(ref)
            try:
                return self.sample(target, name, depth)
            finally:
                self.ref_stack.pop()

        if "const" in schema:
            return schema["const"]
        if "example" in schema:
            return schema["example"]
        examples = schema.get("examples")
        if isinstance(examples, list) and examples:
            return examples[0]
        if isinstance(examples, dict) and examples:
            first = next(iter(examples.values()))
            return first.get("value", first) if isinstance(first, dict) else first
        if "default" in schema:
            return schema["default"]
        enum = schema.get("enum")
        if enum:
            return next((v for v in enum if v is not None), None)

        if schema.get("allOf"):
            return self.sample(self.merge_all_of(schema), name, depth)
        for key in ("oneOf", "anyOf"):
            options = schema.get(key)
            if options:
                for option in options:
                    resolved = self.deref(option)
                    if resolved is not None and resolved.get("type") != "null":
                        return self.sample(option, name, depth)
                return None

        schema_type = schema.get("type")
        if isinstance(schema_type, list):
            schema_type = next((t for t in schema_type if t != "null"), "null")
        if schema_type is None:
            schema_type = self.infer_type(schema)

        if schema_type == "object":
            return self.sample_object(schema, depth)
        if schema_type == "array":
            return self.sample_array(schema, name, depth)
        if schema_type == "string":
            return self.sample_string(schema, name)
        if schema_type == "integer":
            return int(self.sample_number(schema, integer=True))
        if schema_type == "number":
            return self.sample_number(schema, integer=False)
        if schema_type == "boolean":
            return True
        if schema_type == "null":
            return None
        raise ValueError(f"Unsupported schema type: {schema_type!r}")

    def merge_all_of(self, schema: dict) -> dict:
        merged: dict = {k: v for k, v in schema.items() if k != "allOf"}
        properties: dict = dict(schema.get("properties") or {})
        required: list = list(schema.get("required") or [])
        for part in schema["allOf"]:
            resolved = self.deref(part)
            if resolved is None:
                continue
            if resolved.get("allOf"):
                resolved = self.merge_all_of(resolved)
            for key, value in (resolved.get("properties") or {}).items():
                properties.setdefault(key, value)
            required.extend(resolved.get("required") or [])
            for key, value in resolved.items():
                if key not in ("properties", "required"):
                    merged.setdefault(key, value)
        if properties:
            merged["properties"] = properties
        if required:
            merged["required"] = required
        return merged

    @staticmethod
    def infer_type(schema: dict) -> str | None:
        if "properties" in schema or "additionalProperties" in schema:
            return "object"
        if "items" in schema:
            return "array"
        if any(k in schema for k in ("format", "pattern", "minLength", "maxLength")):
            return "string"
        if any(k in schema for k in ("minimum", "maximum", "multipleOf")):
            return "number"
        return "null"

    def sample_object(self, schema: dict, depth: int) -> dict:
        properties = schema.get("properties") or {}
        out = {key: self.sample(sub, key, depth + 1) for key, sub in properties.items()}
        additional = schema.get("additionalProperties")
        if not properties and isinstance(additional, dict):
            out["key"] = self.sample(additional, "key", depth + 1)
        return out

    def sample_array(self, schema: dict, name: str, depth: int) -> list:
        items = schema.get("prefixItems") or schema.get("items")
        if isinstance(items, list):
            return [self.sample(item, name, depth + 1) for item in items]
        count = max(1, schema.get("minItems") or 0)
        if schema.get("maxItems") is not None:
            count = min(count, schema["maxItems"])
        if count == 0 or items is None:
            return []
        value = self.sample(items, name, depth + 1)
        if value is None and self.deref(items) is None:
            return []
        return [value] * count

    def sample_number(self, schema: dict, integer: bool) -> float:
        value: float = 1 if integer else 1.5
        step = 1 if integer else 0.5
        low = schema.get("minimum")
        high = schema.get("maximum")
        excl_low = schema.get("exclusiveMinimum")
        excl_high = schema.get("exclusiveMaximum")
        if isinstance(excl_low, bool):
            excl_low = low if excl_low else None
        if isinstance(excl_high, bool):
            excl_high = high if excl_high else None
        if excl_low is not None:
            low = excl_low + step if low is None else max(low, excl_low + step)
        if excl_high is not None:
            high = excl_high - step if high is None else min(high, excl_high - step)
        if low is not None and value < low:
            value = low
        if high is not None and value > high:
            value = high
        multiple = schema.get("multipleOf")
        if multiple:
            value = math.ceil(value / multiple) * multiple
            if high is not None and value > high:
                value = math.floor(high / multiple) * multiple
        if integer:
            return math.ceil(value)
        return round(float(value), 6)

    def sample_string(self, schema: dict, name: str) -> str:
        candidates = self.format_candidates(schema.get("format"), name)
        candidates.extend(self.name_candidates(name))
        for candidate in candidates:
            if _matches(candidate, schema):
                return candidate
        pattern = schema.get("pattern")
        if pattern:
            generated = self.from_pattern(pattern, name, schema)
            if generated is not None:
                return generated
        return self.fit_length(candidates[0], schema)

    def format_candidates(self, fmt: Any, name: str) -> list[str]:
        if fmt in ("date-time", "date"):
            day = self.today
            if _END_TOKENS.intersection(_name_tokens(name)):
                day += timedelta(days=1)
            iso = day.isoformat()
            if fmt == "date":
                return [iso]
            return [
                f"{iso}T00:00:00Z",
                f"{iso}T00:00Z",
                f"{iso}T00:00:00.000Z",
                f"{iso}T00:00:00+00:00",
            ]
        if fmt == "uuid":
            return [str(uuid.uuid5(uuid.NAMESPACE_URL, name or "sample"))]
        return list(_STATIC_FORMATS.get(fmt, []))

    @staticmethod
    def name_candidates(name: str) -> list[str]:
        tokens = _name_tokens(name)
        if "email" in tokens:
            return ["user@example.com", name]
        if tokens and tokens[-1] in ("url", "uri", "href", "link"):
            return ["https://example.com", name]
        if tokens and tokens[-1] in ("uuid", "guid"):
            return [str(uuid.uuid5(uuid.NAMESPACE_URL, name)), name]
        return [name or "string"]

    @staticmethod
    def from_pattern(pattern: str, name: str, schema: dict) -> str | None:
        seed = zlib.crc32(f"{name}\0{pattern}".encode())
        try:
            generator = rstr.Rstr(random.Random(seed))
            for _ in range(_PATTERN_ATTEMPTS):
                value = generator.xeger(pattern)
                if _matches(value, schema):
                    return value
        except Exception:
            return None
        return None

    @staticmethod
    def fit_length(value: str, schema: dict) -> str:
        max_length = schema.get("maxLength")
        min_length = schema.get("minLength") or 0
        if max_length is not None:
            value = value[:max_length]
        return value.ljust(min_length, "x")
