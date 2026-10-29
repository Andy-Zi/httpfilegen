import json
import textwrap
import warnings

import pytest
from typer.testing import CliRunner

from http_file_generator.models.env_file.env_files import OAuth2Auth
from http_file_generator.models.env_file.generator import (
    OIDC_PLACEHOLDER_AUTH_URL,
    OIDC_PLACEHOLDER_TOKEN_URL,
    EnvAuthWarning,
    generate_env_dicts,
)
from openapi_pydantic.v3.v3_0.open_api import OpenAPI


def _model(security_schemes: dict) -> OpenAPI:
    return OpenAPI.model_validate(
        {
            "openapi": "3.0.3",
            "info": {"title": "T", "version": "1"},
            "paths": {},
            "components": {"securitySchemes": security_schemes},
        }
    )


def _auth_warnings(model: OpenAPI) -> tuple[dict, dict, list[str]]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pub, prv, _ = generate_env_dicts(model, servers=[])
    msgs = [str(w.message) for w in caught if issubclass(w.category, EnvAuthWarning)]
    return pub, prv, msgs


def test_invalid_oauth2_config_warns_with_scheme_and_reason() -> None:
    model = _model(
        {
            "broken": {
                "type": "oauth2",
                "flows": {"clientCredentials": {"tokenUrl": "not-a-url", "scopes": {}}},
            }
        }
    )
    pub, _, msgs = _auth_warnings(model)
    assert "Security" not in pub["dev"]
    assert len(msgs) == 1
    assert "'broken'" in msgs[0]
    assert "public env" in msgs[0]
    assert "Invalid URL: not-a-url" in msgs[0]


def test_implicit_flow_warns() -> None:
    model = _model(
        {
            "imp": {
                "type": "oauth2",
                "flows": {
                    "implicit": {
                        "authorizationUrl": "https://id.example.com/authorize",
                        "scopes": {},
                    }
                },
            }
        }
    )
    _, _, msgs = _auth_warnings(model)
    assert any("'imp'" in m and "implicit" in m for m in msgs)


def test_valid_oauth2_emits_no_warning() -> None:
    model = _model(
        {
            "ok": {
                "type": "oauth2",
                "flows": {
                    "clientCredentials": {
                        "tokenUrl": "https://id.example.com/token",
                        "scopes": {},
                    }
                },
            }
        }
    )
    pub, _, msgs = _auth_warnings(model)
    assert msgs == []
    assert pub["dev"]["Security"]["Auth"]["ok"]["Expires In"] == 3600


def test_openid_connect_generates_authorization_code_skeleton() -> None:
    discovery = "https://id.example.com/.well-known/openid-configuration"
    model = _model({"oidc": {"type": "openIdConnect", "openIdConnectUrl": discovery}})
    pub, prv, msgs = _auth_warnings(model)

    auth = pub["dev"]["Security"]["Auth"]["oidc"]
    assert auth["Type"] == "OAuth2"
    assert auth["Grant Type"] == "Authorization Code"
    assert auth["Auth URL"] == OIDC_PLACEHOLDER_AUTH_URL
    assert auth["Token URL"] == OIDC_PLACEHOLDER_TOKEN_URL
    assert auth["Scope"] == "openid"
    assert auth["Client ID"] == "CHANGE_ME"
    assert "Client Secret" not in auth
    assert prv["dev"]["Security"]["Auth"]["oidc"]["Client Secret"] == "CHANGE_ME"

    assert len(msgs) == 1
    assert "'oidc'" in msgs[0]
    assert discovery in msgs[0]


def test_unsupported_http_scheme_warns() -> None:
    model = _model({"hoba": {"type": "http", "scheme": "hoba"}})
    _, _, msgs = _auth_warnings(model)
    assert any("'hoba'" in m and "unsupported http scheme" in m for m in msgs)


@pytest.mark.parametrize("expires_in", [None, 120])
def test_oauth2_expires_in_default_is_not_ten_seconds(expires_in) -> None:
    cfg = {
        "Grant Type": "Client Credentials",
        "Token URL": "https://id.example.com/token",
        "Client ID": "x",
    }
    if expires_in is not None:
        cfg["Expires In"] = expires_in
    assert OAuth2Auth(**cfg).expires_in == (expires_in or 3600)


def test_cli_env_prints_auth_warnings(cli_app, tmp_path) -> None:
    spec = tmp_path / "s.yaml"
    spec.write_text(
        textwrap.dedent(
            """
            openapi: 3.0.3
            info: {title: S, version: '1'}
            servers:
              - url: https://api.example.com
            paths: {}
            components:
              securitySchemes:
                broken:
                  type: oauth2
                  flows:
                    clientCredentials:
                      tokenUrl: not-a-url
                      scopes: {}
                oidc:
                  type: openIdConnect
                  openIdConnectUrl: https://id.example.com/.well-known/openid-configuration
            """
        )
    )
    res = CliRunner().invoke(cli_app, ["env", str(spec), "--overwrite"])
    assert res.exit_code == 0, res.output
    assert "Warning: Security scheme 'broken'" in res.output
    assert "Warning: Security scheme 'oidc'" in res.output
    pub = json.loads((tmp_path / "http-client.env.json").read_text())
    assert "oidc" in pub["dev"]["Security"]["Auth"]
