from pathlib import Path
from typer.testing import CliRunner

def test_apply_security_api_key_header(cli_app, tmp_path):
    # Build a simple spec with apiKey in header and one GET path
    spec_text = """
openapi: 3.0.3
info:
  title: Sec API
  version: '1.0'
servers:
  - url: https://api.example.com
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
paths:
  /secure:
    get:
      security:
        - ApiKeyAuth: []
      responses:
        '200':
          description: ok
    """
    spec = tmp_path / "sec.yaml"
    spec.write_text(spec_text)

    runner = CliRunner()
    out_file = tmp_path / "secure.http"
    res = runner.invoke(cli_app, ["generate", str(spec), "--out", str(out_file), "--overwrite"])
    assert res.exit_code == 0, res.output

    data = out_file.read_text()
    # Expect header placeholder for API key
    assert "X-API-Key: {{APIKEYAUTH}}" in data


def test_apply_security_api_key_query(cli_app, tmp_path):
    spec_text = """
openapi: 3.0.3
info:
  title: Sec API
  version: '1.0'
servers:
  - url: https://api.example.com
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: query
      name: api_key
paths:
  /secure:
    get:
      security:
        - ApiKeyAuth: []
      responses:
        '200':
          description: ok
    """
    spec = tmp_path / "sec_q.yaml"
    spec.write_text(spec_text)

    runner = CliRunner()
    out_file = tmp_path / "secure_q.http"
    res = runner.invoke(cli_app, ["generate", str(spec), "--out", str(out_file), "--overwrite"])
    assert res.exit_code == 0, res.output

    data = out_file.read_text()
    # Expect query placeholder for API key
    assert "GET {{BASE_URL}}/secure\n?api_key={{APIKEYAUTH}}" in data


def test_apply_security_bearer(cli_app, tmp_path):
    spec_text = """
openapi: 3.0.3
info:
  title: Sec API
  version: '1.0'
servers:
  - url: https://api.example.com
components:
  securitySchemes:
    bearer:
      type: http
      scheme: bearer
paths:
  /secure:
    get:
      security:
        - bearer: []
      responses:
        '200':
          description: ok
    """
    spec = tmp_path / "sec_bearer.yaml"
    spec.write_text(spec_text)

    runner = CliRunner()
    out_file = tmp_path / "secure_bearer.http"
    res = runner.invoke(cli_app, ["generate", str(spec), "--out", str(out_file), "--overwrite"])
    assert res.exit_code == 0, res.output

    data = out_file.read_text()
    # Bearer header placeholder
    assert "Authorization: Bearer {{BEARER_TOKEN}}" in data
