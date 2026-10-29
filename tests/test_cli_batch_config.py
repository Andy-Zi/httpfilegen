import json
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


GENERATE_CONFIG = (
    'mode = "kulala"\nenv_name = "local"\n'
    "include_examples = true\ninclude_schema = true\n"
)


def test_generate_applies_config_defaults(
    cli_app, tmp_path: Path, isolated_home: Path
) -> None:
    _write_config(isolated_home, GENERATE_CONFIG)
    spec = tmp_path / "a.yaml"
    spec.write_text(SPEC)

    res = CliRunner().invoke(cli_app, ["generate", str(spec)])
    assert res.exit_code == 0, res.output
    assert "Kulala" in (tmp_path / "a.http").read_text()
    assert "local" in json.loads((tmp_path / "http-client.env.json").read_text())


def test_generate_explicit_defaults_override_config(
    cli_app, tmp_path: Path, isolated_home: Path, monkeypatch
) -> None:
    import cli

    _write_config(isolated_home, GENERATE_CONFIG)
    spec = tmp_path / "a.yaml"
    spec.write_text(SPEC)
    seen: dict = {}
    original = cli._apply_config_defaults

    def spy(*args):
        result = original(*args)
        seen["result"] = result
        return result

    monkeypatch.setattr(cli, "_apply_config_defaults", spy)

    res = CliRunner().invoke(
        cli_app,
        [
            "generate",
            str(spec),
            "--mode",
            "default",
            "--env-name",
            "dev",
            "--no-include-examples",
            "--no-include-schema",
        ],
    )
    assert res.exit_code == 0, res.output
    mode, _filemode, _base_url, env_name, include_examples, include_schema = seen[
        "result"
    ]
    assert (mode, env_name, include_examples, include_schema) == (
        "default",
        "dev",
        False,
        False,
    )
    assert "Kulala" not in (tmp_path / "a.http").read_text()
    env = json.loads((tmp_path / "http-client.env.json").read_text())
    assert "dev" in env and "local" not in env


def test_batch_explicit_defaults_override_config(
    cli_app, tmp_path: Path, isolated_home: Path
) -> None:
    _write_config(isolated_home, GENERATE_CONFIG)
    (tmp_path / "a.yaml").write_text(SPEC)

    res = CliRunner().invoke(
        cli_app,
        [
            "batch",
            str(tmp_path),
            "--pattern",
            "*.yaml",
            "--mode",
            "default",
            "--env-name",
            "dev",
            "--no-include-examples",
            "--no-include-schema",
        ],
    )
    assert res.exit_code == 0, res.output
    assert "Kulala" not in (tmp_path / "a.http").read_text()
    env = json.loads((tmp_path / "http-client.env.json").read_text())
    assert "dev" in env and "local" not in env


def test_help_shows_documented_defaults(cli_app) -> None:
    res = CliRunner().invoke(cli_app, ["generate", "--help"], env={"COLUMNS": "200"})
    assert res.exit_code == 0
    assert "[default: (default)]" in res.output
    assert "[default: (dev)]" in res.output
    assert "[default: (no-include-examples)]" in res.output
