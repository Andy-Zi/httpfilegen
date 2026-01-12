from pathlib import Path
from typer.testing import CliRunner


def test_batch_include_schema_generates_request_examples(
    cli_app, tmp_path: Path
) -> None:
    # First spec: named examples and plain text
    a = tmp_path / "a.yaml"
    a.write_text(
        """
openapi: 3.0.3
info:
  title: A
  version: '1.0'
servers:
  - url: https://api.example.com
paths:
  /a:
    post:
      requestBody:
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
      responses:
        '200':
          description: ok
""".strip()
    )

    # Second spec: schema fallback only
    b = tmp_path / "b.yaml"
    b.write_text(
        """
openapi: 3.0.3
info:
  title: B
  version: '1.0'
servers:
  - url: https://api.example.com
paths:
  /b:
    post:
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                x:
                  type: integer
      responses:
        '201':
          description: created
""".strip()
    )

    runner = CliRunner()
    res = runner.invoke(
        cli_app,
        [
            "batch",
            str(tmp_path),
            "--pattern",
            "*.yaml",
            "--include-schema",
            "--overwrite",
        ],
    )
    assert res.exit_code == 0, res.output

    a_out = tmp_path / "a.http"
    b_out = tmp_path / "b.http"
    assert a_out.exists()
    assert b_out.exists()

    a_txt = a_out.read_text()
    assert "### Request Examples" in a_txt
    assert "## Request example (application/json - ex1)" in a_txt
    assert "## Request example (application/json - ex2)" in a_txt
    assert "## Request example (text/plain)" in a_txt
    assert "# hello" in a_txt

    b_txt = b_out.read_text()
    assert "### Request Examples" in b_txt
    assert "## Request example (application/json)" in b_txt
