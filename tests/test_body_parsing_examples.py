from http_file_generator.models.utils.body_parsing import handle_body
from http_file_generator.models.http_file.var import HttpVariable

class Media:
    def __init__(self, example=None, examples=None, schema=None):
        self.example = example
        self.examples = examples
        self.media_type_schema = schema

class Schema:
    def __init__(self, d):
        self._d = d
    def model_dump(self, **kwargs):
        return self._d

class RequestBody:
    def __init__(self, content):
        self.content = content


def test_handle_body_with_example_precedence():
    rb = RequestBody({
        "application/json": Media(example={"x": 1}, schema=Schema({"type": "object"}))
    })
    out = handle_body("/x", rb)
    assert "application/json" in out
    body, headers = out["application/json"]
    assert body == {"x": 1}
    assert headers["Content-Type"] == "application/json"


def test_handle_body_with_examples_precedence():
    rb = RequestBody({
        "application/json": Media(examples={"a": {"foo": "bar"}}, schema=Schema({"type": "object"}))
    })
    out = handle_body("/x", rb)
    body, _ = out["application/json"]
    # our code returns the first example object
    assert body == {"foo": "bar"} or (hasattr(body, "value") and getattr(body, "value") == {"foo": "bar"})
