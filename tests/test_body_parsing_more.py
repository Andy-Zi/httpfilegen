import pytest
from http_file_generator.models.utils.body_parsing import handle_body


class Schema:
    def __init__(self, d):
        self._d = d
    def model_dump(self, **kwargs):
        return self._d

class Media:
    def __init__(self, example=None, examples=None, schema=None):
        self.example = example
        self.examples = examples
        self.media_type_schema = schema

class RequestBody:
    def __init__(self, content):
        self.content = content


def test_handle_body_schema_generation_and_headers():
    rb = RequestBody({
        "application/json": Media(schema=Schema({
            "type": "object",
            "properties": {"x": {"type": "integer"}},
        }))
    })
    out = handle_body("/x", rb)
    assert "application/json" in out
    body, headers = out["application/json"]
    assert isinstance(body, dict)
    assert headers["Content-Type"] == "application/json"


def test_handle_body_empty_request_returns_empty():
    out = handle_body("/x", None)
    assert out == {}
