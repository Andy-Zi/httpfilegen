from typing import Any, Literal
from pydantic import (
    BaseModel,
    Field,
    model_validator,
    ValidationError,
    ConfigDict,
    field_validator,
)
import re
import os


def validate_url(value: str | None) -> str | None:
    if value is None:
        return value
    # Simple regex for HTTP/HTTPS URLs, including localhost and IPs
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
        r"localhost|"  # localhost
        r"127\.0\.0\.1|"  # 127.0.0.1
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)?$",
        re.IGNORECASE,
    )  # optional path
    if not url_pattern.match(value):
        raise ValueError(f"Invalid URL: {value}")
    return value


class OAuth2Auth(BaseModel):
    type_: str = Field(default="OAuth2", alias="Type")
    grant_type: Literal[
        "Authorization Code",
        "Client Credentials",
        "Device Authorization",
        "Implicit",
        "Password",
    ] = Field(alias="Grant Type")
    auth_url: str | None = Field(default=None, alias="Auth URL")
    token_url: str = Field(alias="Token URL", min_length=1)
    redirect_url: str | None = Field(default=None, alias="Redirect URL")
    revoke_url: str | None = Field(default=None, alias="Revoke URL")
    client_id: str = Field(alias="Client ID", min_length=1)
    client_secret: str | None = Field(
        default=None, alias="Client Secret"
    )  # Store in private.env.json
    device_auth_url: str | None = Field(default=None, alias="Device Auth URL")
    response_type: str | None = Field(default=None, alias="Response Type")
    client_credentials: Literal["none", "in body", "basic", "jwt"] = Field(
        default="basic", alias="Client Credentials"
    )
    pkce: bool | dict[str, Any] | None = Field(default=None, alias="PKCE")
    assertion: str | None = Field(default=None, alias="Assertion")
    jwt: dict[str, Any] | None = Field(default=None, alias="JWT")
    scope: str | None = Field(default=None, alias="Scope")
    expires_in: int = Field(default=10, alias="Expires In")
    acquire_automatically: bool = Field(default=True, alias="Acquire Automatically")
    username: str | None = Field(default=None, alias="Username")
    password: str | None = Field(default=None, alias="Password")
    custom_request_parameters: dict[str, Any] | None = Field(
        default=None, alias="Custom Request Parameters"
    )
    use_id_token: bool = Field(default=False, alias="Use ID Token")

    @field_validator(
        "auth_url",
        "token_url",
        "redirect_url",
        "revoke_url",
        "device_auth_url",
        mode="before",
    )
    @classmethod
    def validate_urls(cls, v):
        return validate_url(v)

    @model_validator(mode="after")
    def validate_oauth2(self) -> "OAuth2Auth":
        gt = self.grant_type
        if gt == "Authorization Code":
            if not self.auth_url:
                raise ValueError(
                    "Auth URL is required for Authorization Code grant type"
                )
            if not self.token_url:
                raise ValueError(
                    "Token URL is required for Authorization Code grant type"
                )
        elif gt == "Client Credentials":
            if not self.token_url:
                raise ValueError(
                    "Token URL is required for Client Credentials grant type"
                )
            if not self.client_secret:
                raise ValueError(
                    "Client Secret is required for Client Credentials grant type"
                )
        elif gt == "Device Authorization":
            if not self.device_auth_url:
                raise ValueError(
                    "Device Auth URL is required for Device Authorization grant type"
                )
            if not self.token_url:
                raise ValueError(
                    "Token URL is required for Device Authorization grant type"
                )
        elif gt == "Implicit":
            if not self.auth_url:
                raise ValueError("Auth URL is required for Implicit grant type")
        elif gt == "Password":
            if not self.username or not self.password:
                raise ValueError(
                    "Username and Password are required for Password grant type"
                )
        # Set default response_type if not set
        if gt in ["Authorization Code", "Implicit"] and not self.response_type:
            self.response_type = "code" if gt == "Authorization Code" else "token"
        # Validate PKCE
        if isinstance(self.pkce, dict):
            if "Code Challenge Method" not in self.pkce:
                raise ValueError("PKCE dict must contain 'Code Challenge Method'")
            method = self.pkce["Code Challenge Method"]
            if method not in ["Plain", "S256"]:
                raise ValueError("Code Challenge Method must be 'Plain' or 'S256'")
        # Validate JWT
        if self.jwt:
            if "Header" not in self.jwt or "Payload" not in self.jwt:
                raise ValueError("JWT must contain 'Header' and 'Payload'")
            header = self.jwt["Header"]
            if (
                not isinstance(header, dict)
                or "alg" not in header
                or "typ" not in header
            ):
                raise ValueError("JWT Header must be dict with 'alg' and 'typ'")
            if header["alg"] not in ["RS256", "HS256"]:
                raise ValueError("JWT alg must be 'RS256' or 'HS256'")
            if header["typ"] != "JWT":
                raise ValueError("JWT typ must be 'JWT'")
            payload = self.jwt["Payload"]
            if not isinstance(payload, dict):
                raise ValueError("JWT Payload must be dict")
            for key in ["exp", "iat"]:
                if key in payload and not isinstance(payload[key], int):
                    raise ValueError(f"JWT Payload {key} must be int")
        # Validate custom_request_parameters
        if self.custom_request_parameters:
            for k, v in self.custom_request_parameters.items():
                if isinstance(v, dict):
                    if "Value" not in v:
                        raise ValueError(f"Custom param {k} dict must have 'Value'")
                    if "Use" in v and v["Use"] not in [
                        "Everywhere",
                        "In Auth Request",
                        "In Token Request",
                    ]:
                        raise ValueError(
                            f"Custom param {k} 'Use' must be one of the allowed values"
                        )
        return self


class BasicAuth(BaseModel):
    type_: str = Field(default="Basic", alias="Type")
    username: str = Field(alias="Username", min_length=1)
    password: str = Field(alias="Password", min_length=1)


class DigestAuth(BaseModel):
    type_: str = Field(default="Digest", alias="Type")
    username: str = Field(alias="Username", min_length=1)
    password: str = Field(alias="Password", min_length=1)


class NTLMAuth(BaseModel):
    type_: str = Field(default="NTLM", alias="Type")
    username: str | None = Field(default=None, alias="Username")
    password: str | None = Field(default=None, alias="Password")

    @model_validator(mode="after")
    def validate_ntlm(self) -> "NTLMAuth":
        if self.username and not self.password:
            raise ValueError("Password is required if Username is provided for NTLM")
        if self.password and not self.username:
            raise ValueError("Username is required if Password is provided for NTLM")
        return self


class NegotiateAuth(BaseModel):
    type_: str = Field(default="Negotiate", alias="Type")


class BearerAuth(BaseModel):
    type_: str = Field(default="Bearer", alias="Type")
    token: str = Field(alias="Token", min_length=1)


class AWSSignatureV4Auth(BaseModel):
    type_: str = Field(default="AWS", alias="Type")
    access_key_id: str = Field(alias="Access Key Id", min_length=1)
    secret_access_key: str = Field(alias="Secret Access Key", min_length=1)
    session_token: str | None = Field(default=None, alias="Session Token")
    region: str = Field(alias="Region", min_length=1)
    service: str = Field(alias="Service", min_length=1)


class SSLClientCertAuth(BaseModel):
    type_: str = Field(default="SSL", alias="Type")
    cert: str = Field(alias="Cert", min_length=1)
    key: str = Field(alias="Key", min_length=1)

    @field_validator("cert", "key")
    @classmethod
    def validate_file_exists(cls, v):
        if not os.path.isfile(v):
            raise ValueError(f"Certificate file does not exist: {v}")
        return v


# Union for all auth types
AuthConfig = (
    OAuth2Auth
    | BasicAuth
    | DigestAuth
    | NTLMAuth
    | NegotiateAuth
    | BearerAuth
    | AWSSignatureV4Auth
    | SSLClientCertAuth
)


class Security(BaseModel):
    auth: dict[str, AuthConfig] = Field(
        default_factory=dict, alias="Auth"
    )  # Keyed by auth-id, e.g., "my-oauth"


class EnvSection(BaseModel):
    default_headers: dict[str, str] | None = Field(
        default=None, alias="$default_headers"
    )
    security: Security | None = Field(default=None, alias="Security")

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_variables(self) -> "EnvSection":
        for key, value in self.model_extra.items():
            if not re.match(r"^[A-Za-z0-9_]+$", key):
                raise ValueError(
                    f"Variable key '{key}' does not match required pattern ^[A-Za-z0-9_]+$"
                )
            if not isinstance(value, (str, int, float, dict)):
                raise ValueError(
                    f"Variable value for '{key}' must be string, number, or object (dict)"
                )
        return self


class HttpClientBaseEnv(BaseModel):
    schema_: str | None = Field(
        default=None,
        alias="$schema",
    )
    shared: EnvSection | None = Field(default=None, alias="$shared")

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_extra(self) -> "HttpClientBaseEnv":
        for key, value in self.model_extra.items():
            if not isinstance(value, dict):
                raise ValueError(f"Extra key '{key}' must be a dict")
            try:
                EnvSection(**value)
            except ValidationError as e:
                raise ValueError(f"Invalid EnvSection for '{key}': {e}")
        return self


class HttpClientPrivateEnv(HttpClientBaseEnv):
    schema_: str = Field(
        default="https://raw.githubusercontent.com/mistweaverco/kulala.nvim/main/schemas/http-client.env.schema.json",
        alias="$schema",
    )


class HttpClientEnv(HttpClientBaseEnv):
    schema_: str = Field(
        default="https://raw.githubusercontent.com/mistweaverco/kulala.nvim/main/schemas/http-client.private.env.schema.json",
        alias="$schema",
    )
