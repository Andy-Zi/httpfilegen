from pathlib import Path
from typer.testing import CliRunner


def test_examples_sections_do_not_break_requests(cli_app, tmp_path: Path) -> None:
    # Ensure that examples headers don't create new requests and remain commented
    spec = tmp_path / "ex.yaml"
    spec.write_text(
        """
openapi: 3.0.3
info:
  title: E
  version: '1.0'
servers:
  - url: https://api.example.com
paths:
  /x:
    get:
      responses:
        '200':
          description: ok
          content:
            application/json:
              example:
                v: 1
""".strip()
    )

    runner = CliRunner()
    out = tmp_path / "ex.http"
    res = runner.invoke(
        cli_app,
        [
            "generate",
            str(spec),
            "--out",
            str(out),
            "--include-examples",
            "--overwrite",
        ],
    )
    assert res.exit_code == 0, res.output
    txt = out.read_text()

    # Should contain one Request separator, not more due to examples
    assert txt.count("### Request:") == 1
    # Examples header present
    assert "### Response Examples" in txt
    # Commented values
    assert "# {" in txt
    assert '# "v": 1' in txt or '"v": 1' in txt
