from pathlib import Path
from typer.testing import CliRunner


def test_generate_single_include_examples_from_schema(
    cli_app, sample_spec_path, tmp_path: Path
) -> None:
    runner = CliRunner()
    out_file = tmp_path / "with_examples.http"
    res = runner.invoke(
        cli_app,
        [
            "generate",
            str(sample_spec_path),
            "--out",
            str(out_file),
            "--include-examples",
            "--overwrite",
        ],
    )
    assert res.exit_code == 0, res.output
    data = out_file.read_text()
    # Expect a JSON response example for 200
    assert "## Response example (200 application/json)" in data
    assert "# {" in data  # commented JSON starts
    # For POST /items 201 without content, expect placeholder
    assert "## Response example (201)" in data
    assert "# <no example available>" in data


def test_generate_single_include_examples_named_and_multi_content(
    cli_app, tmp_path: Path
) -> None:
    # Spec with multiple content types and named examples
    spec = tmp_path / "multi.yaml"
    spec.write_text(
        """
openapi: 3.0.3
info:
  title: Multi
  version: '1.0'
servers:
  - url: https://api.example.com
paths:
  /multi:
    get:
      responses:
        '200':
          description: ok
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
              example: ok
""".strip()
    )

    runner = CliRunner()
    out_file = tmp_path / "multi.http"
    res = runner.invoke(
        cli_app,
        [
            "generate",
            str(spec),
            "--out",
            str(out_file),
            "--include-examples",
            "--overwrite",
        ],
    )
    assert res.exit_code == 0, res.output
    content = out_file.read_text()
    # Named examples should include names in header
    assert "## Response example (200 application/json - ex1)" in content
    assert "## Response example (200 application/json - ex2)" in content
    # Plain text content type example should render as commented plain text
    assert "## Response example (200 text/plain)" in content
    assert "# ok" in content
