import json
import textwrap
from pathlib import Path

from typer.testing import CliRunner

from http_file_generator.models.env_file.generator import (
    BASE_URL_PLACEHOLDER,
    OIDC_PLACEHOLDER_AUTH_URL,
    is_placeholder,
    merge_env_dicts,
)
from http_file_generator.overrides import PLACEHOLDER_TOKEN_URL


def _read(path: Path) -> dict:
    return json.loads(path.read_text())


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


def test_merge_keeps_user_values_and_replaces_placeholders() -> None:
    existing = {
        "dev": {
            "BASE_URL": "https://mine.example.com",
            "TOKEN": "CHANGE_ME",
            "Security": {
                "Auth": {
                    "oauth": {
                        "Client ID": "my-client",
                        "Token URL": PLACEHOLDER_TOKEN_URL,
                    }
                }
            },
            "EXTRA": "keep",
        },
        "staging": {"BASE_URL": "https://staging.example.com"},
    }
    generated = {
        "dev": {
            "BASE_URL": "https://spec.example.com",
            "TOKEN": "CHANGE_ME_TOO",
            "NEW_VAR": "CHANGE_ME",
            "Security": {
                "Auth": {
                    "oauth": {
                        "Client ID": "CHANGE_ME",
                        "Token URL": "https://auth.example.com/token",
                        "Scope": "read",
                    }
                }
            },
        }
    }

    merged = merge_env_dicts(existing, generated)

    dev = merged["dev"]
    assert dev["BASE_URL"] == "https://mine.example.com"
    assert dev["TOKEN"] == "CHANGE_ME_TOO"
    assert dev["NEW_VAR"] == "CHANGE_ME"
    assert dev["EXTRA"] == "keep"
    assert dev["Security"]["Auth"]["oauth"] == {
        "Client ID": "my-client",
        "Token URL": "https://auth.example.com/token",
        "Scope": "read",
    }
    assert merged["staging"] == {"BASE_URL": "https://staging.example.com"}


def test_merge_replaces_base_url_placeholder() -> None:
    merged = merge_env_dicts(
        {"dev": {"BASE_URL": BASE_URL_PLACEHOLDER}},
        {"dev": {"BASE_URL": "https://api.example.com"}},
    )
    assert merged["dev"]["BASE_URL"] == "https://api.example.com"


def test_change_me_urls_are_placeholders() -> None:
    assert is_placeholder(PLACEHOLDER_TOKEN_URL)
    assert is_placeholder(OIDC_PLACEHOLDER_AUTH_URL)
    assert is_placeholder("https://CHANGE-ME.example.com/anything")
    assert not is_placeholder("https://auth.example.com/token")


def test_merge_replaces_auth_entry_when_type_changes() -> None:
    existing = {
        "dev": {
            "Security": {
                "Auth": {
                    "api": {"Type": "Bearer", "Token": "abc"},
                    "mine": {"Type": "Basic", "Username": "me", "Password": "pw"},
                }
            }
        }
    }
    generated = {
        "dev": {
            "Security": {
                "Auth": {
                    "api": {
                        "Type": "OAuth2",
                        "Grant Type": "Client Credentials",
                        "Client ID": "CHANGE_ME",
                        "Token URL": PLACEHOLDER_TOKEN_URL,
                    }
                }
            }
        }
    }

    auth = merge_env_dicts(existing, generated)["dev"]["Security"]["Auth"]

    assert auth["api"] == generated["dev"]["Security"]["Auth"]["api"]
    assert auth["mine"] == existing["dev"]["Security"]["Auth"]["mine"]


def test_merge_replaces_auth_entry_when_grant_type_changes() -> None:
    existing = {
        "Auth": {
            "oauth": {
                "Type": "OAuth2",
                "Grant Type": "Authorization Code",
                "Client ID": "my-client",
                "Auth URL": "https://auth.example.com/authorize",
                "Token URL": OIDC_PLACEHOLDER_AUTH_URL,
                "Response Type": "code",
            }
        }
    }
    generated = {
        "Auth": {
            "oauth": {
                "Type": "OAuth2",
                "Grant Type": "Client Credentials",
                "Client ID": "CHANGE_ME",
                "Token URL": "https://auth.example.com/token",
            }
        }
    }

    entry = merge_env_dicts(existing, generated)["Auth"]["oauth"]

    assert entry == {
        "Type": "OAuth2",
        "Grant Type": "Client Credentials",
        "Client ID": "my-client",
        "Token URL": "https://auth.example.com/token",
    }


def test_override_switch_to_oauth2_replaces_bearer_entry(
    cli_app, tmp_path: Path
) -> None:
    spec = tmp_path / "api.yaml"
    spec.write_text(
        textwrap.dedent(
            """
            openapi: 3.0.3
            info: {title: A, version: '1.0'}
            servers: [{url: https://api.example.com}]
            security: [{bearerAuth: []}]
            paths:
              /a:
                get:
                  responses:
                    '200': {description: ok}
            components:
              securitySchemes:
                bearerAuth: {type: http, scheme: bearer}
            """
        )
    )
    runner = CliRunner()
    args = ["env", str(spec), "--out-dir", str(tmp_path)]
    assert runner.invoke(cli_app, args).exit_code == 0
    public = tmp_path / "http-client.env.json"
    pub = _read(public)
    pub["dev"]["Security"] = {
        "Auth": {"bearerAuth": {"Type": "Bearer", "Token": "abc"}}
    }
    _write(public, pub)

    res = runner.invoke(cli_app, ["override", "oauth2", str(spec)])
    assert res.exit_code == 0, res.output
    res = runner.invoke(cli_app, args)
    assert res.exit_code == 0, res.output

    entry = _read(public)["dev"]["Security"]["Auth"]["bearerAuth"]
    assert entry["Type"] == "OAuth2"
    assert entry["Grant Type"] == "Client Credentials"
    assert "Token" not in entry


def _fill_in(tmp_path: Path) -> None:
    public = tmp_path / "http-client.env.json"
    private = tmp_path / "http-client.private.env.json"
    pub = _read(public)
    pub["dev"]["BASE_URL"] = "https://mine.example.com"
    pub["dev"]["Security"]["Auth"]["oauth"]["Client ID"] = "my-client"
    pub["local"] = {"BASE_URL": "http://localhost:8080"}
    _write(public, pub)
    prv = _read(private)
    prv["dev"]["Security"]["Auth"]["oauth"]["Client Secret"] = "s3cret"
    _write(private, prv)


def _assert_filled_in_kept(tmp_path: Path) -> None:
    pub = _read(tmp_path / "http-client.env.json")
    prv = _read(tmp_path / "http-client.private.env.json")
    assert pub["dev"]["BASE_URL"] == "https://mine.example.com"
    assert pub["dev"]["Security"]["Auth"]["oauth"]["Client ID"] == "my-client"
    assert pub["local"] == {"BASE_URL": "http://localhost:8080"}
    assert prv["dev"]["Security"]["Auth"]["oauth"]["Client Secret"] == "s3cret"


def test_generate_overwrite_merges_env_files(
    cli_app, sample_spec_path: Path, tmp_path: Path
) -> None:
    runner = CliRunner()
    out = tmp_path / "out.http"
    args = ["generate", str(sample_spec_path), "--out", str(out)]
    assert runner.invoke(cli_app, args).exit_code == 0
    _fill_in(tmp_path)

    res = runner.invoke(cli_app, [*args, "--overwrite"])
    assert res.exit_code == 0, res.output
    _assert_filled_in_kept(tmp_path)


def test_generate_merges_env_files_without_overwrite(
    cli_app, sample_spec_path: Path, tmp_path: Path
) -> None:
    runner = CliRunner()
    out = tmp_path / "out.http"
    args = ["generate", str(sample_spec_path), "--out", str(out)]
    assert runner.invoke(cli_app, args).exit_code == 0
    _fill_in(tmp_path)
    out.unlink()

    res = runner.invoke(cli_app, args)
    assert res.exit_code == 0, res.output
    assert out.exists()
    _assert_filled_in_kept(tmp_path)


def test_env_command_merges_existing_files(
    cli_app, sample_spec_path: Path, tmp_path: Path
) -> None:
    runner = CliRunner()
    args = ["env", str(sample_spec_path), "--out-dir", str(tmp_path)]
    assert runner.invoke(cli_app, args).exit_code == 0
    _fill_in(tmp_path)

    res = runner.invoke(cli_app, args)
    assert res.exit_code == 0, res.output
    _assert_filled_in_kept(tmp_path)


def test_batch_overwrite_merges_env_files(
    cli_app, sample_spec_path: Path, tmp_path: Path
) -> None:
    runner = CliRunner()
    args = ["batch", str(sample_spec_path)]
    assert runner.invoke(cli_app, args).exit_code == 0
    _fill_in(tmp_path)

    res = runner.invoke(cli_app, [*args, "--overwrite"])
    assert res.exit_code == 0, res.output
    _assert_filled_in_kept(tmp_path)


def test_env_command_rejects_invalid_existing_json(
    cli_app, sample_spec_path: Path, tmp_path: Path
) -> None:
    public = tmp_path / "http-client.env.json"
    public.write_text("{not json")

    res = CliRunner().invoke(
        cli_app, ["env", str(sample_spec_path), "--out-dir", str(tmp_path)]
    )
    assert res.exit_code != 0
    assert "invalid JSON env file" in res.output
    assert public.read_text() == "{not json"


def test_no_base_url_warning_when_user_filled_it_in(cli_app, tmp_path: Path) -> None:
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        textwrap.dedent(
            """
            openapi: 3.0.3
            info: {title: A, version: '1.0'}
            paths:
              /a:
                get:
                  responses:
                    '200': {description: ok}
            """
        )
    )
    runner = CliRunner()
    args = ["env", str(spec), "--out-dir", str(tmp_path)]
    first = runner.invoke(cli_app, args)
    assert "No valid base URL" in first.output
    public = tmp_path / "http-client.env.json"
    pub = _read(public)
    pub["dev"]["BASE_URL"] = "https://mine.example.com"
    _write(public, pub)

    second = runner.invoke(cli_app, args)
    assert second.exit_code == 0, second.output
    assert "No valid base URL" not in second.output
    assert _read(public)["dev"]["BASE_URL"] == "https://mine.example.com"
