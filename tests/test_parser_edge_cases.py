from http_file_generator.models.http_file.open_api_parser import OpenApiParser

def test_paths_without_responses(tmp_path):
    spec = tmp_path / "noresp.yaml"
    spec.write_text(
        """
openapi: 3.0.3
info:
  title: X
  version: '1.0'
servers:
  - url: https://api.example.com
paths:
  /empty:
    get:
      responses:
        '204':
          description: no content
        """
    )
    p = OpenApiParser(spec)
    bodies = p.get_response_body("/empty")
    assert "GET" in bodies and isinstance(bodies["GET"], dict)


def test_no_servers(tmp_path):
    spec = tmp_path / "nosrv.yaml"
    spec.write_text(
        """
openapi: 3.0.3
info:
  title: X
  version: '1.0'
paths: {}
        """
    )
    p = OpenApiParser(spec)
    # Some parsers may inject a default server of '/'; allow list of zero or one
    assert isinstance(p.get_server(), list)
