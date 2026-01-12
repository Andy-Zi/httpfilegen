from http_file_generator.models.env_file.env_files import (
    OAuth2Auth,
    PrivateOAuth2Auth,
    validate_url,
)
import pytest


def test_oauth2auth_validation_urls_and_defaults() -> None:
    # Valid auth code flow with PKCE
    auth = OAuth2Auth(
        **{
            "Type": "OAuth2",
            "Grant Type": "Authorization Code",
            "Auth URL": "https://auth.example.com/authorize",
            "Token URL": "https://auth.example.com/token",
            "Client ID": "id",
            "PKCE": {"Code Challenge Method": "S256"},
        }
    )
    assert auth.response_type == "code"

    # Invalid URL should raise
    with pytest.raises(ValueError):
        OAuth2Auth(
            **{
                "Type": "OAuth2",
                "Grant Type": "Client Credentials",
                "Token URL": "not_a_url",
                "Client ID": "id",
                "Client Secret": "secret",
            }
        )


def test_private_oauth2auth_partial_secrets() -> None:
    # Private can accept partial secret configuration
    prv = PrivateOAuth2Auth(**{"Client Secret": "secret"})
    assert prv.client_secret == "secret"


def test_validate_url_helper() -> None:
    assert validate_url("https://example.com") == "https://example.com"
    assert validate_url("http://localhost:8080/api") == "http://localhost:8080/api"
    with pytest.raises(ValueError):
        validate_url("ftp://example.com")
