from http_file_generator.models.utils.parameter_parsing import handle_missing_path_parasm, handle_query_params
from http_file_generator.models.http_file.var import HttpVariable


def test_handle_missing_path_params():
    path, params = handle_missing_path_parasm("/users/{id}")
    assert path == "/users/{id}"
    assert any(p.name == "id" for p in params)


def test_handle_query_params_append():
    # Minimal fake Parameter object with only needed attributes
    class P:
        name = "q"
        example = None
        examples = None
        description = ""
        class Schema:
            def model_dump(self, **kwargs):
                return {"type": "string"}
        param_schema = Schema()

    path, var = handle_query_params("/x", P())
    assert path.endswith("\n?q={{q}}")
    assert isinstance(var, HttpVariable)
    assert var.name == "q"
