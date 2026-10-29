import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from http_file_generator.overrides import (
    bearer_to_oauth2_patch,
    find_override,
    is_override_file,
    merge_patch,
)

SPEC = """
openapi: 3.0.3
info:
  title: A
  version: '1.0'
servers:
  - url: https://api.example.com
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    ApiKey:
      type: apiKey
      in: header
      name: X-Key
paths:
  /items:
    get:
      security:
        - BearerAuth: []
      responses:
        '200':
          description: ok
""".strip()

BEARER_HEADER = "Authorization: Bearer {{BEARERAUTH_TOKEN}}"
OAUTH_HEADER = 'Authorization: Bearer {{$auth.token("BearerAuth")}}'


def _write_spec(tmp_path: Path) -> Path:
    spec = tmp_path / "api.yaml"
    spec.write_text(SPEC)
    return spec


def test_merge_patch_merges_nested_and_deletes_null() -> None:
    target = {"a": {"b": 1, "c": 2}, "d": [1, 2]}
    patch = {"a": {"b": None, "e": 3}, "d": [3]}
    assert merge_patch(target, patch) == {"a": {"c": 2, "e": 3}, "d": [3]}
    assert target == {"a": {"b": 1, "c": 2}, "d": [1, 2]}


def test_find_override_and_is_override_file(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path)
    assert find_override(spec) is None
    override = tmp_path / "api_override.json"
    override.write_text("{}")
    assert find_override(spec) == override
    assert is_override_file(override)
    assert not is_override_file(spec)


def test_bearer_to_oauth2_patch_only_converts_bearer() -> None:
    patch = bearer_to_oauth2_patch(
        yaml.safe_load(SPEC), token_url="https://id.example.com/token", scopes=["r"]
    )
    schemes = patch["components"]["securitySchemes"]
    assert list(schemes) == ["BearerAuth"]
    assert schemes["BearerAuth"]["type"] == "oauth2"
    assert schemes["BearerAuth"]["scheme"] is None
    flow = schemes["BearerAuth"]["flows"]["clientCredentials"]
    assert flow == {"tokenUrl": "https://id.example.com/token", "scopes": {"r": ""}}


def test_override_oauth2_command_writes_yaml_next_to_spec(
    cli_app, tmp_path: Path
) -> None:
    spec = _write_spec(tmp_path)
    runner = CliRunner()
    res = runner.invoke(
        cli_app,
        ["override", "oauth2", str(spec), "--token-url", "https://id.example.com/t"],
    )
    assert res.exit_code == 0, res.output
    override = tmp_path / "api_override.yaml"
    data = yaml.safe_load(override.read_text())
    flow = data["components"]["securitySchemes"]["BearerAuth"]["flows"]
    assert flow["clientCredentials"]["tokenUrl"] == "https://id.example.com/t"

    res = runner.invoke(cli_app, ["override", "oauth2", str(spec)])
    assert res.exit_code != 0
    assert "overwrite" in res.output.lower()


def test_override_oauth2_command_fails_without_bearer(cli_app, tmp_path: Path) -> None:
    spec = tmp_path / "api.json"
    spec.write_text(json.dumps({"openapi": "3.0.3", "paths": {}}))
    res = CliRunner().invoke(cli_app, ["override", "oauth2", str(spec)])
    assert res.exit_code == 1
    assert not (tmp_path / "api_override.json").exists()


def test_generate_applies_override_automatically(cli_app, tmp_path: Path) -> None:
    spec = _write_spec(tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli_app, ["override", "oauth2", str(spec)]).exit_code == 0

    res = runner.invoke(cli_app, ["generate", str(spec), "--no-env"])
    assert res.exit_code == 0, res.output
    assert "Using override" in res.output
    assert OAUTH_HEADER in (tmp_path / "api.http").read_text()

    res = runner.invoke(
        cli_app, ["generate", str(spec), "--no-env", "--no-override", "--overwrite"]
    )
    assert res.exit_code == 0, res.output
    assert BEARER_HEADER in (tmp_path / "api.http").read_text()


def test_generate_explicit_override_path(cli_app, tmp_path: Path) -> None:
    spec = _write_spec(tmp_path)
    override = tmp_path / "custom.json"
    runner = CliRunner()
    res = runner.invoke(
        cli_app, ["override", "oauth2", str(spec), "--out", str(override)]
    )
    assert res.exit_code == 0, res.output

    res = runner.invoke(
        cli_app, ["generate", str(spec), "--no-env", "--override", str(override)]
    )
    assert res.exit_code == 0, res.output
    assert OAUTH_HEADER in (tmp_path / "api.http").read_text()

    res = runner.invoke(
        cli_app,
        ["generate", str(spec), "--override", str(tmp_path / "missing.json")],
    )
    assert res.exit_code == 1


def test_batch_skips_override_files_and_applies_them(cli_app, tmp_path: Path) -> None:
    spec = _write_spec(tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli_app, ["override", "oauth2", str(spec)]).exit_code == 0

    res = runner.invoke(cli_app, ["batch", str(tmp_path), "--no-env"])
    assert res.exit_code == 0, res.output
    assert "OK: 1  Failed: 0" in res.output
    assert OAUTH_HEADER in (tmp_path / "api.http").read_text()
    assert not (tmp_path / "api_override.http").exists()
