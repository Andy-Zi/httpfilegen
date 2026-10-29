from pathlib import Path

from typer.testing import CliRunner

SPEC = """
openapi: 3.0.3
info:
  title: A
  version: '1.0'
servers:
  - url: https://api.example.com
paths:
  /a:
    get:
      responses:
        '200':
          description: ok
""".strip()


def _write_config(home: Path, content: str) -> None:
    config_dir = home / ".config" / "httpfilegen"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text(content)


def test_batch_applies_config_defaults(
    cli_app, tmp_path: Path, isolated_home: Path
) -> None:
    _write_config(
        isolated_home,
        'mode = "kulala"\nfilemode = "multi"\nenv_name = "local"\n',
    )
    (tmp_path / "a.yaml").write_text(SPEC)

    res = CliRunner().invoke(cli_app, ["batch", str(tmp_path), "--pattern", "*.yaml"])
    assert res.exit_code == 0, res.output

    tree = tmp_path / "a"
    index = tree / "a" / "index.http"
    assert index.exists()
    assert not (tmp_path / "a.http").exists()
    assert "Kulala" in index.read_text()
    assert '"local"' in (tree / "http-client.env.json").read_text()


def test_batch_cli_options_override_config(
    cli_app, tmp_path: Path, isolated_home: Path
) -> None:
    _write_config(isolated_home, 'mode = "kulala"\nfilemode = "multi"\n')
    (tmp_path / "a.yaml").write_text(SPEC)

    res = CliRunner().invoke(
        cli_app,
        ["batch", str(tmp_path), "--pattern", "*.yaml", "--filemode", "single"],
    )
    assert res.exit_code == 0, res.output

    out = tmp_path / "a.http"
    assert out.exists()
    assert not (tmp_path / "a").exists()
    assert "Kulala" in out.read_text()
