from http_file_generator.models.utils.parameter_parsing import handle_params

class Loc:
    def __init__(self, v):
        self.value = v

class ExampleObj:
    def __init__(self, value):
        self.value = value

class Param:
    def __init__(self, name, where, example=None, examples=None):
        self.name = name
        self.param_in = Loc(where)
        self.description = ""
        self.example = example
        self.examples = examples
        self.param_schema = None


def test_examples_object_value_for_param():
    p = Param("foo", "query", examples={"e1": ExampleObj("bar")})
    path, vars = handle_params("/x", [p])
    assert any(v.name == "foo" and v.value == "bar" for v in vars)
    assert "\n?foo={{foo}}" in path
