from typer.testing import CliRunner

def _run_and_get(cli_app, spec_text: str, path: str):
    from pathlib import Path
    from tempfile import TemporaryDirectory

    runner = CliRunner()
    with TemporaryDirectory() as d:
        spec = Path(d) / "s.yaml"
        spec.write_text(spec_text)
        out = Path(d) / "o.http"
        res = runner.invoke(cli_app, ["generate", str(spec), "--out", str(out), "--overwrite"])
        assert res.exit_code == 0, res.output
        return out.read_text()


def test_http_basic_and_digest(cli_app):
    spec = """
openapi: 3.0.3
info:
  title: t
  version: '1.0'
servers:
  - url: https://api.example.com
components:
  securitySchemes:
    basic:
      type: http
      scheme: basic
    digest:
      type: http
      scheme: digest
paths:
  /x:
    get:
      security:
        - basic: []
      responses:
        '200':
          description: ok
  /y:
    get:
      security:
        - digest: []
      responses:
        '200':
          description: ok
"""
    data = _run_and_get(cli_app, spec, "/x")
    assert "Authorization: Basic {{BASIC_USERNAME}}:{{BASIC_PASSWORD}}" in data
    assert "Authorization: Digest {{DIGEST_USERNAME}}:{{DIGEST_PASSWORD}}" in data


def test_http_ntlm_and_negotiate(cli_app):
    spec = """
openapi: 3.0.3
info:
  title: t
  version: '1.0'
servers:
  - url: https://api.example.com
components:
  securitySchemes:
    nt:
      type: http
      scheme: ntlm
    neg:
      type: http
      scheme: negotiate
paths:
  /x:
    get:
      security:
        - nt: []
      responses:
        '200':
          description: ok
  /y:
    get:
      security:
        - neg: []
      responses:
        '200':
          description: ok
"""
    data = _run_and_get(cli_app, spec, "/x")
    assert "Authorization: NTLM" in data
    assert "Authorization: Negotiate" in data


def test_api_key_cookie(cli_app):
    spec = """
openapi: 3.0.3
info:
  title: t
  version: '1.0'
servers:
  - url: https://api.example.com
components:
  securitySchemes:
    k:
      type: apiKey
      in: cookie
      name: session
paths:
  /z:
    get:
      security:
        - k: []
      responses:
        '200':
          description: ok
"""
    data = _run_and_get(cli_app, spec, "/z")
    assert "Cookie: session={{K}}" in data
