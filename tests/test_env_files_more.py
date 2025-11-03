from http_file_generator.models.env_file.env_files import OAuth2Auth, PrivateOAuth2Auth
import pytest


def test_oauth2_implicit_requires_auth_url():
    with pytest.raises(ValueError):
        OAuth2Auth(
            **{
                "Type": "OAuth2",
                "Grant Type": "Implicit",
                "Client ID": "id",
                # missing Auth URL
                "Token URL": "https://id.example.com/token",
            }
        )


def test_oauth2_device_authorization_requires_device_url():
    with pytest.raises(ValueError):
        OAuth2Auth(
            **{
                "Type": "OAuth2",
                "Grant Type": "Device Authorization",
                "Token URL": "https://id.example.com/token",
                "Client ID": "id",
                # missing Device Auth URL
            }
        )


def test_private_oauth2_permissive_accepts_partial():
    prv = PrivateOAuth2Auth(**{"Grant Type": "Client Credentials", "Client Secret": "s"})
    assert prv.client_secret == "s"