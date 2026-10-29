from pathlib import Path

from typer.testing import CliRunner

PARAM = """
      parameters:
        - name: mrid
          in: path
          required: true
          schema:
            type: string
"""

OK = """
      responses:
        '200':
          description: ok
"""


def _generate(cli_app, tmp_path: Path, paths: str) -> Path:
    spec = tmp_path / "api.yaml"
    spec.write_text(
        "openapi: 3.0.3\n"
        "info:\n  title: T\n  version: '1.0'\n"
        "servers:\n  - url: https://api.example.com\n"
        "paths:\n" + paths
    )
    res = CliRunner().invoke(
        cli_app,
        ["generate", str(spec), "--out", str(tmp_path / "api.http"), "-f", "multi"],
    )
    assert res.exit_code == 0, res.output
    return tmp_path / "api"


def _dirs(tree: Path) -> set[str]:
    return {p.relative_to(tree).as_posix() for p in tree.rglob("index.http")}


def test_path_params_use_brace_free_directories(cli_app, tmp_path: Path) -> None:
    tree = _generate(
        cli_app,
        tmp_path,
        "  /bids/{mrid}:\n    get:"
        + PARAM
        + OK
        + "  /bids/{mrid}/acknowledgement:\n    post:"
        + PARAM
        + OK,
    )

    assert _dirs(tree) == {
        "bids/_mrid_/index.http",
        "bids/_mrid_/acknowledgement/index.http",
    }
    assert not any("{" in p.name or "}" in p.name for p in tree.rglob("*"))

    content = (tree / "bids/_mrid_/acknowledgement/index.http").read_text()
    assert "POST {{BASE_URL}}/bids/{{mrid}}/acknowledgement" in content


def test_path_param_directory_avoids_literal_sibling(cli_app, tmp_path: Path) -> None:
    tree = _generate(
        cli_app,
        tmp_path,
        "  /bids/{mrid}/acknowledgement:\n    get:"
        + PARAM
        + OK
        + "  /bids/_MRID_:\n    get:"
        + OK
        + "  /bids/{mrid}.json:\n    get:"
        + PARAM
        + OK,
    )

    assert _dirs(tree) == {
        "bids/__mrid__/acknowledgement/index.http",
        "bids/_MRID_/index.http",
        "bids/_mrid_.json/index.http",
    }
    literal = (tree / "bids/_MRID_/index.http").read_text()
    assert "GET {{BASE_URL}}/bids/_MRID_" in literal
    param = (tree / "bids/__mrid__/acknowledgement/index.http").read_text()
    assert "GET {{BASE_URL}}/bids/{{mrid}}/acknowledgement" in param
