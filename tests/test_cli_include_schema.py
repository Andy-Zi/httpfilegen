from pathlib import Path
from typer.testing import CliRunner

def test_generate_include_schema_and_examples(cli_app, tmp_path: Path):
    spec = tmp_path / "req_examples.yaml"
    spec.write_text(
        """
openapi: 3.0.3
info:
  title: ReqEx
  version: '1.0'
servers:
  - url: https://api.example.com
paths:
  /r:
    post:
      requestBody:
        required: false
        content:
          application/json:
            examples:
              ex1:
                value:
                  a: 1
              ex2:
                value:
                  b: 2
          text/plain:
            example: hello
          application/x.sample+json:
            schema:
              type: object
              properties:
                c:
                  type: integer
      responses:
        '200':
          description: ok
          content:
            application/json:
              example:
                ok: true
            text/plain:
              example: done
""".strip()
    )

    runner = CliRunner()
    out = tmp_path / "req_examples.http"
    res = runner.invoke(
        cli_app,
        [
            "generate",
            str(spec),
            "--out",
            str(out),
            "--include-schema",
            "--include-examples",
            "--overwrite",
        ],
    )
    assert res.exit_code == 0, res.output
    data = out.read_text()

    # Request examples header and named examples
    assert "### Request Examples" in data
    assert "## Request example (application/json - ex1)" in data
    assert "## Request example (application/json - ex2)" in data
    # Plain text example rendered commented
    assert "## Request example (text/plain)" in data
    assert "# hello" in data
    # Schema fallback example for custom content-type
    assert "## Request example (application/x.sample+json)" in data

    # Response examples header and both content types
    assert "### Response Examples" in data
    assert "## Response example (200 application/json)" in data
    assert "# {" in data  # commented JSON
    assert "## Response example (200 text/plain)" in data
    assert "# done" in data
