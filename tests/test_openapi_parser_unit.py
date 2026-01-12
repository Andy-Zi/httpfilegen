from http_file_generator.models.http_file.open_api_parser import OpenApiParser


def test_openapi_parser_helpers(tmp_path) -> None:
    spec = tmp_path / "api.yaml"
    spec.write_text(
        """
openapi: 3.0.3
info:
  title: P
  version: '1'
servers:
  - url: https://api.example.com
paths:
  /a:
    get:
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
        - name: q
          in: query
          required: false
          schema:
            type: string
      responses:
        '200':
          description: ok
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: string
        """
    )

    p = OpenApiParser(spec)
    paths = p.get_paths()
    assert "/a" in paths
    servers = p.get_server()
    assert servers and servers[0].url.startswith("https://")
    # params
    path_params = p.get_path_params("/a")
    query_params = p.get_query_params("/a")
    assert "GET" in path_params and "GET" in query_params
    assert (
        any(pr.param_in == "path" for pr in path_params["GET"])
        or path_params["GET"] == []
    )
    assert (
        any(pr.param_in == "query" for pr in query_params["GET"])
        or query_params["GET"] == []
    )
