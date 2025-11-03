from http_file_generator.models.http_file.open_api_parser import OpenApiParser
import json


def test_multi_content_types_and_no_request_body(tmp_path):
    spec = tmp_path / "s.yaml"
    spec.write_text(
        """
openapi: 3.0.3
info:
  title: S
  version: '1.0'
servers:
  - url: https://api.example.com
paths:
  /ct:
    get:
      responses:
        '200':
          description: ok
          content:
            application/json:
              examples:
                e1:
                  value:
                    ok: true
            text/plain:
              examples:
                e2:
                  value: "plain"
  /norb:
    get:
      responses:
        '204':
          description: no content
        
        """
    )
    p = OpenApiParser(spec)
    rb = p.get_request_body("/norb")
    assert rb.get("GET") is None or rb.get("GET") == {}

    resp = p.get_response_body("/ct")
    assert "GET" in resp
    json_ct = resp["GET"]["200"].get("application/json")
    txt_ct = resp["GET"]["200"].get("text/plain")
    assert json_ct and json_ct["ok"] is True
    assert txt_ct == "plain"
