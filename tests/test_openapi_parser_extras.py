from typer.testing import CliRunner


def test_parser_path_and_query_extraction(cli_app, tmp_path) -> None:
    spec_text = """
openapi: 3.0.3
info:
  title: P
  version: '1.0'
servers:
  - url: https://api.example.com
paths:
  /users/{id}:
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
    spec = tmp_path / "p.yaml"
    spec.write_text(spec_text)

    runner = CliRunner()
    out_file = tmp_path / "users.http"
    res = runner.invoke(
        cli_app, ["generate", str(spec), "--out", str(out_file), "--overwrite"]
    )
    assert res.exit_code == 0, res.output

    content = out_file.read_text()
    # Expect path templating and query line
    assert "GET {{BASE_URL}}/users/{{id}}" in content
    assert "\n?q={{q}}" in content or "\n&q={{q}}" in content
