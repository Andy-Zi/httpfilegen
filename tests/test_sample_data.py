import re
from datetime import date
from types import SimpleNamespace

import pytest

from http_file_generator.models.utils import parameter_parsing as pp
from http_file_generator.models.utils.body_parsing import handle_body
from http_file_generator.models.utils.sample_data import (
    generate_sample,
    reference_date,
)

TODAY = date(2026, 10, 29)


def gen(schema: dict):
    return generate_sample(schema, TODAY)


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"type": "string", "const": "c", "example": "e"}, "c"),
        ({"type": "string", "example": "e", "default": "d"}, "e"),
        ({"type": "string", "examples": ["x", "y"], "default": "d"}, "x"),
        ({"type": "string", "examples": {"one": {"value": "v"}}}, "v"),
        ({"type": "integer", "default": 0}, 0),
        ({"type": "string", "enum": [None, "b", "c"]}, "b"),
        ({"type": "boolean", "example": False}, False),
    ],
)
def test_spec_values_take_priority(schema: dict, expected) -> None:
    assert gen(schema) == expected


@pytest.mark.parametrize(
    ("fmt", "expected"),
    [
        ("date", "2026-10-29"),
        ("date-time", "2026-10-29T00:00:00Z"),
        ("email", "user@example.com"),
        ("uri", "https://example.com"),
        ("ipv4", "192.0.2.1"),
        ("ipv6", "2001:db8::1"),
        ("duration", "PT15M"),
    ],
)
def test_string_formats(fmt: str, expected: str) -> None:
    assert gen({"type": "string", "format": fmt}) == expected


def test_uuid_is_valid_and_stable_per_name() -> None:
    schema = {
        "type": "object",
        "properties": {
            "a": {"type": "string", "format": "uuid"},
            "b": {"type": "string", "format": "uuid"},
        },
    }
    out = gen(schema)
    uuid_re = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    assert re.match(uuid_re, out["a"])
    assert out["a"] != out["b"]
    assert gen(schema) == out


def test_end_like_dates_follow_start() -> None:
    props = {
        k: {"type": "string", "format": "date-time"}
        for k in ("start", "end", "validTo", "createdDateTime")
    }
    out = gen({"type": "object", "properties": props})
    assert out["start"] == "2026-10-29T00:00:00Z"
    assert out["createdDateTime"] == "2026-10-29T00:00:00Z"
    assert out["end"] == "2026-10-30T00:00:00Z"
    assert out["validTo"] == "2026-10-30T00:00:00Z"


def test_date_time_variant_matching_pattern() -> None:
    schema = {
        "type": "string",
        "format": "date-time",
        "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$",
    }
    assert gen(schema) == "2026-10-29T00:00Z"


def test_pattern_is_satisfied_and_deterministic() -> None:
    schema = {"type": "string", "pattern": "^[A-Z]{3}-[0-9]{4}$"}
    value = gen(schema)
    assert re.match(schema["pattern"], value)
    assert gen(schema) == value


def test_plain_strings_use_property_name_and_lengths() -> None:
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "code": {"type": "string", "maxLength": 2},
            "id": {"type": "string", "minLength": 5},
            "contactEmail": {"type": "string"},
            "homepageUrl": {"type": "string"},
        },
    }
    assert gen(schema) == {
        "status": "status",
        "code": "co",
        "id": "idxxx",
        "contactEmail": "user@example.com",
        "homepageUrl": "https://example.com",
    }
    assert gen({"type": "string"}) == "string"


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"type": "integer"}, 1),
        ({"type": "number"}, 1.5),
        ({"type": "integer", "minimum": 10, "maximum": 20}, 10),
        ({"type": "integer", "maximum": -5}, -5),
        ({"type": "integer", "exclusiveMinimum": 1}, 2),
        ({"type": "integer", "minimum": 1, "exclusiveMinimum": True}, 2),
        ({"type": "integer", "maximum": 1, "exclusiveMaximum": True}, 0),
        ({"type": "number", "exclusiveMaximum": 1}, 0.5),
        ({"type": "integer", "multipleOf": 5}, 5),
        ({"type": "number", "multipleOf": 0.1}, 1.5),
        ({"type": "integer", "minimum": 0, "maximum": 7, "multipleOf": 5}, 5),
    ],
)
def test_numbers_respect_bounds(schema: dict, expected) -> None:
    assert gen(schema) == expected


def test_arrays_respect_item_counts() -> None:
    items = {"type": "integer"}
    assert gen({"type": "array", "items": items}) == [1]
    assert gen({"type": "array", "items": items, "minItems": 3}) == [1, 1, 1]
    assert gen({"type": "array", "items": items, "maxItems": 0}) == []
    assert gen({"type": "array"}) == []
    assert gen({"type": "array", "prefixItems": [items, {"type": "boolean"}]}) == [
        1,
        True,
    ]


def test_composition_and_nullable_types() -> None:
    schema = {
        "type": "object",
        "properties": {
            "merged": {
                "allOf": [
                    {"type": "object", "properties": {"a": {"type": "integer"}}},
                    {"properties": {"b": {"type": "boolean"}}, "required": ["b"]},
                ]
            },
            "choice": {"oneOf": [{"type": "null"}, {"type": "integer"}]},
            "any": {"anyOf": [{"type": "string", "format": "date"}]},
            "nullable": {"type": ["null", "integer"]},
            "only_null": {"type": "null"},
            "map": {"type": "object", "additionalProperties": {"type": "integer"}},
        },
    }
    assert gen(schema) == {
        "merged": {"a": 1, "b": True},
        "choice": 1,
        "any": "2026-10-29",
        "nullable": 1,
        "only_null": None,
        "map": {"key": 1},
    }


def test_all_of_ref_keeps_referenced_example() -> None:
    schema = {
        "type": "object",
        "properties": {"id": {"allOf": [{"$ref": "#/$defs/Id"}], "description": "x"}},
        "$defs": {"Id": {"type": "string", "example": "ABC-1"}},
    }
    assert gen(schema) == {"id": "ABC-1"}


def test_refs_resolve_and_recursion_terminates() -> None:
    schema = {
        "$ref": "#/$defs/Node",
        "$defs": {
            "Node": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "parent": {"$ref": "#/$defs/Node"},
                    "children": {"type": "array", "items": {"$ref": "#/$defs/Node"}},
                    "external": {"$ref": "other.json#/Thing"},
                },
            }
        },
    }
    assert gen(schema) == {
        "name": "name",
        "parent": None,
        "children": [],
        "external": None,
    }


def test_type_is_inferred_when_missing() -> None:
    assert gen({"properties": {"a": {"format": "date"}}}) == {"a": "2026-10-29"}
    assert gen({"items": {"minimum": 3}}) == [3]
    assert gen({}) is None


def test_unknown_type_raises() -> None:
    with pytest.raises(ValueError):
        gen({"type": "something_invalid"})


def test_reference_date_honours_source_date_epoch(monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1767225600")
    assert reference_date() == date(2026, 1, 1)
    assert generate_sample({"type": "string", "format": "date"}) == "2026-01-01"
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "not-a-number")
    assert isinstance(reference_date(), date)


def test_handle_body_uses_property_examples() -> None:
    schema = SimpleNamespace(
        model_dump=lambda **_: {
            "type": "object",
            "properties": {
                "mrId": {"type": "string", "example": "RBD_1"},
                "createdDateTime": {"type": "string", "format": "date-time"},
            },
        }
    )
    media = SimpleNamespace(example=None, examples=None, media_type_schema=schema)
    body = SimpleNamespace(content={"application/json": media})
    out = handle_body("/p", body)
    sample, headers = out["application/json"]
    assert sample["mrId"] == "RBD_1"
    assert re.match(r"^\d{4}-\d{2}-\d{2}T00:00:00Z$", sample["createdDateTime"])
    assert headers == {"Content-Type": "application/json"}


def test_falsy_param_example_keeps_priority() -> None:
    param = SimpleNamespace(
        name="page",
        param_in="query",
        example=0,
        examples=None,
        param_schema=None,
        description=None,
    )
    _, var = pp.handle_query_params("/items", param)
    assert var.value == "0"


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"type": "integer", "minimum": 0, "maximum": 0}, "0"),
        ({"type": "boolean", "default": False}, "False"),
        ({"type": "null"}, ""),
        ({"type": "array", "items": {"type": "integer"}, "maxItems": 0}, ""),
    ],
)
def test_falsy_generated_param_values_are_kept(schema: dict, expected: str) -> None:
    param = SimpleNamespace(
        name="flag",
        param_in="header",
        example=None,
        examples=None,
        param_schema=SimpleNamespace(model_dump=lambda **_: schema),
        description=None,
    )
    assert pp.handle_header_params("/p", param).value == expected
