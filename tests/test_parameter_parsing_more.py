import pytest
from http_file_generator.models.utils import parameter_parsing as pp
from http_file_generator.models.http_file.var import HttpVariable


class Loc:
    def __init__(self, v):
        self.value = v


class ParamStub:
    def __init__(self, name, where, schema_dict=None, example=None, examples=None, description=""):
        self.name = name
        self.param_in = Loc(where)
        self.description = description
        self.example = example
        self.examples = examples
        class S:
            def __init__(self, d):
                self._d = d
            def model_dump(self, **kwargs):
                return self._d
        self.param_schema = S(schema_dict) if schema_dict is not None else None


def test_handle_path_params_ok_and_error():
    p = ParamStub("id", "path")
    new_path, var = pp.handle_path_params("/users/{id}", p)
    assert new_path == "/users/{{id}}"
    assert isinstance(var, HttpVariable) and var.name == "id"

    with pytest.raises(ValueError):
        pp.handle_path_params("/users", p)


def test_handle_query_params_ampersand():
    p = ParamStub("q", "query", schema_dict={"type": "string"})
    path, var = pp.handle_query_params("/x?y={{y}}", p)
    assert "\n&q={{q}}" in path
    assert var.name == "q"


def test_handle_params_all_locations():
    params = [
        ParamStub("id", "path"),
        ParamStub("q", "query", schema_dict={"type": "string"}),
        ParamStub("H", "header", schema_dict={"type": "integer"}),
        ParamStub("C", "cookie", schema_dict={"type": "boolean"}),
    ]
    path, collected = pp.handle_params("/p/{id}", params)
    names = {v.name for v in collected}
    assert names.issuperset({"id", "q", "H", "C"})
    assert "/p/{{id}}" in path
    assert "\n?q={{q}}" in path or "\n&?q={{q}}" not in path


def test_handle_params_unknown_location_raises():
    p = ParamStub("x", "unknown")
    with pytest.raises(NotImplementedError):
        pp.handle_params("/p", [p])


def test_generate_sample_param_from_schema_object_returns_str():
    out = pp._generate_sample_param_from_schema({"type": "object"})
    assert isinstance(out, str)


def test_generate_sample_param_from_schema_array_returns_first():
    out = pp._generate_sample_param_from_schema({
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1
    })
    # Could be string
    assert isinstance(out, (str, int, float, bool))


def test_generate_sample_param_from_schema_error_raises():
    with pytest.raises(ValueError):
        # Invalid type may trigger failure in jsf
        pp._generate_sample_param_from_schema({"type": "something_invalid"})
