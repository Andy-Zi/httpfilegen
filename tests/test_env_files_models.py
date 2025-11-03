import os
import tempfile
import pytest

from http_file_generator.models.env_file.env_files import (
    OAuth2Auth,
    PrivateOAuth2Auth,
    BasicAuth,
    DigestAuth,
    NTLMAuth,
    BearerAuth,
    AWSSignatureV4Auth,
    SSLClientCertAuth,
    EnvSection,
    PrivateEnvSection,
    HttpClientPrivateEnv,
)


def test_basic_and_digest_auth_valid():
    b = BasicAuth(**{"Username": "u", "Password": "p"})
    d = DigestAuth(**{"Username": "u", "Password": "p"})
    assert b.username == "u" and d.password == "p"


def test_ntlm_requires_both_or_none():
    with pytest.raises(ValueError):
        NTLMAuth(**{"Username": "x"})
    with pytest.raises(ValueError):
        NTLMAuth(**{"Password": "x"})
    # both provided should pass
    nt = NTLMAuth(**{"Username": "u", "Password": "p"})
    assert nt.username == "u" and nt.password == "p"


def test_bearer_auth_valid():
    b = BearerAuth(**{"Token": "tok"})
    assert b.token == "tok"


def test_aws_signature_v4_auth_valid():
    aws = AWSSignatureV4Auth(
        **{
            "Access Key Id": "AKIA...",
            "Secret Access Key": "SECRET",
            "Region": "eu-west-1",
            "Service": "execute-api",
        }
    )
    assert aws.region == "eu-west-1"


def test_ssl_client_cert_auth_validates_files(tmp_path):
    cert = tmp_path / "c.crt"
    key = tmp_path / "k.key"
    cert.write_text("x")
    key.write_text("y")
    ssl = SSLClientCertAuth(**{"Cert": cert.as_posix(), "Key": key.as_posix()})
    assert ssl.cert.endswith("c.crt")
    # missing file should raise
    with pytest.raises(ValueError):
        SSLClientCertAuth(**{"Cert": cert.as_posix(), "Key": (tmp_path / "no.key").as_posix()})


def test_oauth2_password_requires_username_and_password():
    with pytest.raises(ValueError):
        OAuth2Auth(
            **{
                "Type": "OAuth2",
                "Grant Type": "Password",
                "Token URL": "https://id.example.com/token",
                "Client ID": "id",
            }
        )


def test_oauth2_client_credentials_requirements():
    with pytest.raises(ValueError):
        OAuth2Auth(
            **{
                "Type": "OAuth2",
                "Grant Type": "Client Credentials",
                "Token URL": "https://id.example.com/token",
                "Client ID": "id",
                # missing Client Secret should error
            }
        )


def test_oauth2_pkce_validation():
    with pytest.raises(ValueError):
        OAuth2Auth(
            **{
                "Type": "OAuth2",
                "Grant Type": "Authorization Code",
                "Auth URL": "https://auth.example.com/authorize",
                "Token URL": "https://auth.example.com/token",
                "Client ID": "id",
                "PKCE": {"Code Challenge Method": "INVALID"},
            }
        )
    with pytest.raises(ValueError):
        OAuth2Auth(
            **{
                "Type": "OAuth2",
                "Grant Type": "Authorization Code",
                "Auth URL": "https://auth.example.com/authorize",
                "Token URL": "https://auth.example.com/token",
                "Client ID": "id",
                "PKCE": {},
            }
        )


def test_oauth2_jwt_validation():
    with pytest.raises(ValueError):
        OAuth2Auth(
            **{
                "Type": "OAuth2",
                "Grant Type": "Client Credentials",
                "Token URL": "https://id.example.com/token",
                "Client ID": "id",
                "Client Secret": "secret",
                "JWT": {"Header": {"alg": "RS256", "typ": "JWT"}},
            }
        )
    with pytest.raises(ValueError):
        OAuth2Auth(
            **{
                "Type": "OAuth2",
                "Grant Type": "Client Credentials",
                "Token URL": "https://id.example.com/token",
                "Client ID": "id",
                "Client Secret": "secret",
                "JWT": {"Header": {"alg": "bad", "typ": "JWT"}, "Payload": {}},
            }
        )


def test_custom_request_parameters_validation():
    with pytest.raises(ValueError):
        OAuth2Auth(
            **{
                "Type": "OAuth2",
                "Grant Type": "Client Credentials",
                "Token URL": "https://id.example.com/token",
                "Client ID": "id",
                "Client Secret": "secret",
                "Custom Request Parameters": {"foo": {"Use": "Everywhere"}},
            }
        )
    with pytest.raises(ValueError):
        OAuth2Auth(
            **{
                "Type": "OAuth2",
                "Grant Type": "Client Credentials",
                "Token URL": "https://id.example.com/token",
                "Client ID": "id",
                "Client Secret": "secret",
                "Custom Request Parameters": {"foo": {"Value": "x", "Use": "Somewhere"}},
            }
        )
    # Valid custom params
    ok = OAuth2Auth(
        **{
            "Type": "OAuth2",
            "Grant Type": "Client Credentials",
            "Token URL": "https://id.example.com/token",
            "Client ID": "id",
            "Client Secret": "secret",
            "Custom Request Parameters": {"foo": {"Value": "x", "Use": "Everywhere"}},
        }
    )
    assert ok.custom_request_parameters["foo"]["Value"] == "x"


def test_private_env_section_variables_validation():
    # invalid key pattern
    with pytest.raises(ValueError):
        PrivateEnvSection(**{"BAD-KEY": "x"})
    # invalid value type
    with pytest.raises(ValueError):
        PrivateEnvSection(**{"GOOD": [1, 2, 3]})
    # valid extras
    sec = PrivateEnvSection(**{"GOOD": "x", "NUM": 5, "OBJ": {"a": 1}})
    assert getattr(sec, "GOOD") == "x"


def test_httpclientprivateenv_validate_extra():
    # Extra environment key must be a dict representing a section
    with pytest.raises(ValueError):
        HttpClientPrivateEnv(**{"$shared": {}, "dev": "notadict"})
    # Valid nested section
    model = HttpClientPrivateEnv(**{"$shared": {}, "dev": PrivateEnvSection(**{"X": "Y"}).model_dump(by_alias=True, exclude_none=True)})
    assert hasattr(model, "dev")
