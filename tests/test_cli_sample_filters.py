import json
from typer.testing import CliRunner


def test_sample_filters(cli_app, tmp_path) -> None:
    spec_text = """
openapi: 3.0.3
info:
  title: T
  version: '1.0'
servers:
  - url: https://api.example.com
paths:
  /r:
    get:
      requestBody:
        required: false
        content:
          application/json:
            schema:
              type: object
              properties:
                a:
                  type: integer
      responses:
        '200':
          description: ok
          content:
            application/json:
              schema:
                type: object
                properties:
                  ok:
                    type: boolean
        '404':
          description: nf
    """
    spec = tmp_path / "t.yaml"
    spec.write_text(spec_text)

    runner = CliRunner()

    # Sample filtered by method, status and content-type
    res = runner.invoke(
        cli_app,
        [
            "sample",
            str(spec),
            "/r",
            "--method",
            "get",
            "--status",
            "200",
            "--content-type",
            "application/json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["path"] == "/r"
    assert "request" in data
    assert "response" in data
    # response should include only 200 with application/json
    resp = data["response"]["GET"]
    assert "200" in resp
    assert "application/json" in resp["200"]

    # Filter by status 404 (no content) should produce empty or None mapping
    res2 = runner.invoke(
        cli_app,
        [
            "sample",
            str(spec),
            "/r",
            "--method",
            "get",
            "--status",
            "404",
        ],
    )
    assert res2.exit_code == 0, res2.output
    data2 = json.loads(res2.output)
    assert "GET" in data2["response"]
    # 404 may map to empty dict
    assert "404" in data2["response"]["GET"]
