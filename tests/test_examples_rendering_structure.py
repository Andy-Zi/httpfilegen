from pathlib import Path

import pytest
from typer.testing import CliRunner

from http_file_generator.models.http_file.request import SEPARATOR


@pytest.mark.parametrize("mode", ["default", "kulala", "pycharm", "vscode"])
def test_examples_sections_do_not_break_requests(
    cli_app, tmp_path: Path, mode: str
) -> None:
    # Example sections must stay comments and never open a new request block
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
    post:
      requestBody:
        content:
          application/json:
            example:
              w: 2
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
            "--include-schema",
            "--mode",
            mode,
            "--overwrite",
        ],
    )
    assert res.exit_code == 0, res.output
    txt = out.read_text()
    lines = txt.splitlines()

    assert "# Request Examples" in lines
    assert "# Response Examples" in lines
    assert '#   "v": 1' in lines
    assert '#   "w": 2' in lines

    # Every '###' line belongs to the request banner (two separators around it)
    separator = SEPARATOR.rstrip("\n")
    banner_ends = [i for i, ln in enumerate(lines) if ln == separator]
    assert len(banner_ends) == 2
    for i, ln in enumerate(lines):
        if ln.startswith("###"):
            assert banner_ends[0] <= i <= banner_ends[1], ln
