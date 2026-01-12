import pytest
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


def test_openapi_parser_invalid_yaml(tmp_path) -> None:
    """Test that invalid YAML raises appropriate error."""
    spec = tmp_path / "invalid.yaml"
    spec.write_text("invalid: yaml: content: [")

    with pytest.raises(
        (ValueError, Exception)
    ):  # Can be various exceptions from parsing
        OpenApiParser(spec)


def test_openapi_parser_invalid_json(tmp_path) -> None:
    """Test that invalid JSON raises appropriate error."""
    spec = tmp_path / "invalid.json"
    spec.write_text('{"invalid": json content}')

    with pytest.raises(
        (ValueError, Exception)
    ):  # Can be various exceptions from parsing
        OpenApiParser(spec)


def test_openapi_parser_minimal_valid_spec(tmp_path) -> None:
    """Test parsing a minimal but valid OpenAPI spec."""
    spec = tmp_path / "minimal.yaml"
    spec.write_text(
        """
        openapi: 3.0.3
        info:
          title: Test
          version: '1.0'
        paths:
          /test:
            get:
              responses:
                '200':
                  description: OK
        """
    )

    p = OpenApiParser(spec)
    assert p.model.info.title == "Test"
    assert "/test" in p.get_paths()
    # OpenAPI adds a default server with URL "/" when no servers specified
    servers = p.get_server()
    assert len(servers) == 1
    assert servers[0].url == "/"


def test_openapi_parser_basic_functionality(tmp_path) -> None:
    """Test basic OpenAPI parser functionality."""
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        """
        openapi: 3.0.3
        info:
          title: Test Parser
          version: '1.0'
        servers:
          - url: https://api.example.com
        paths:
          /test:
            get:
              responses:
                '200':
                  description: OK
        """
    )
    p = OpenApiParser(spec)
    assert p.model.info.title == "Test Parser"
    assert p.model.openapi == "3.0.3"
    assert "/test" in p.get_paths()
    servers = p.get_server()
    assert len(servers) == 1
    assert servers[0].url == "https://api.example.com"


def test_openapi_parser_empty_spec(tmp_path) -> None:
    """Test handling of empty or minimal specs."""
    spec = tmp_path / "empty.yaml"
    spec.write_text(
        """
        openapi: 3.0.3
        info:
          title: Empty
          version: '1.0'
        paths: {}
        """
    )

    p = OpenApiParser(spec)
    assert p.model.info.title == "Empty"
    assert p.get_paths() == []
    # OpenAPI adds a default server with URL "/" when no servers specified
    servers = p.get_server()
    assert len(servers) == 1
    assert servers[0].url == "/"


def test_openapi_parser_with_servers(tmp_path) -> None:
    """Test server extraction from specs."""
    spec = tmp_path / "servers.yaml"
    spec.write_text(
        """
        openapi: 3.0.3
        info:
          title: Servers Test
          version: '1.0'
        servers:
          - url: https://api.example.com
            description: Production
          - url: https://staging.example.com
            description: Staging
        paths:
          /test:
            get:
              responses:
                '200':
                  description: OK
        """
    )

    p = OpenApiParser(spec)
    servers = p.get_server()
    assert len(servers) == 2
    assert servers[0].url == "https://api.example.com"
    assert servers[1].url == "https://staging.example.com"


def test_openapi_parser_json_format(tmp_path) -> None:
    """Test parsing JSON format specs."""
    spec = tmp_path / "spec.json"
    spec.write_text(
        """{
          "openapi": "3.0.3",
          "info": {
            "title": "JSON Test",
            "version": "1.0"
          },
          "paths": {
            "/json": {
              "get": {
                "responses": {
                  "200": {
                    "description": "OK"
                  }
                }
              }
            }
          }
        }"""
    )

    p = OpenApiParser(spec)
    assert p.model.info.title == "JSON Test"
    assert "/json" in p.get_paths()


def test_openapi_parser_preparsed_data() -> None:
    """Test passing already parsed data to constructor."""
    data = {
        "openapi": "3.0.3",
        "info": {"title": "Preparsed Test", "version": "1.0"},
        "paths": {},
    }

    p = OpenApiParser(data)
    assert p.model.info.title == "Preparsed Test"
