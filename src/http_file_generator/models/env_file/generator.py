from __future__ import annotations
from typing import Union

from http_file_generator.models.env_file.env_files import (
    HttpClientEnv,
    HttpClientPrivateEnv,
    Security,
    EnvSection,
)
from http_file_generator.models.env_file.env_files import (
    PrivateEnvSection,
    PrivateSecurity,
    OAuth2Auth,
    PrivateOAuth2Auth,
)

from openapi_pydantic.v3.v3_0 import SecurityScheme as SecurityScheme3_0
from openapi_pydantic.v3.v3_1 import SecurityScheme as SecurityScheme3_1
from openapi_pydantic.v3.v3_0 import Reference as Reference3_0
from openapi_pydantic.v3.v3_1 import Reference as Reference3_1
from openapi_pydantic.v3.v3_1.open_api import OpenAPI as OpenAPI3_1
from openapi_pydantic.v3.v3_0.open_api import OpenAPI as OpenAPI3_0

SecurityScheme = Union[SecurityScheme3_0, SecurityScheme3_1]
Reference = Union[Reference3_0, Reference3_1]
OpenAPI = Union[OpenAPI3_0, OpenAPI3_1]

# Note: Public env uses the public schema; private env uses the private schema
PUBLIC_SCHEMA_URL = "https://raw.githubusercontent.com/mistweaverco/kulala.nvim/main/schemas/http-client.env.schema.json"
PRIVATE_SCHEMA_URL = "https://raw.githubusercontent.com/mistweaverco/kulala.nvim/main/schemas/http-client.private.env.schema.json"


def _sanitize(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name).upper()


def _choose_oauth2_flow(scheme: SecurityScheme) -> tuple[str, dict] | None:
    flows = getattr(scheme, "flows", None)
    if not flows:
        return None
    # Preference order
    ordered = [
        ("authorizationCode", getattr(flows, "authorizationCode", None)),
        ("clientCredentials", getattr(flows, "clientCredentials", None)),
        ("password", getattr(flows, "password", None)),
        ("implicit", getattr(flows, "implicit", None)),
    ]
    for name, flow in ordered:
        if flow is not None:
            # Convert to grant type label used by Kulala config
            grant_map = {
                "authorizationCode": "Authorization Code",
                "clientCredentials": "Client Credentials",
                "password": "Password",
                "implicit": "Implicit",
            }
            return grant_map[name], flow.model_dump(exclude_none=True)
    return None


def _flow_scopes_str(flow_dict: dict) -> str | None:
    scopes = flow_dict.get("scopes") or {}
    if not scopes:
        return None
    return " ".join(sorted(scopes.keys()))


def _build_oauth2_public_config(
    scheme_name: str, scheme: SecurityScheme
) -> dict | None:
    chosen = _choose_oauth2_flow(scheme)
    if not chosen:
        # missing flows; cannot build a valid typed config
        return None
    grant_type, flow = chosen
    # Skip implicit to avoid failing required Token URL in typed model
    if grant_type == "Implicit":
        return None
    cfg: dict = {
        "Type": "OAuth2",
        "Grant Type": grant_type,
        "Client ID": "CHANGE_ME",
    }
    # Fill URLs per flow
    if grant_type in ("Authorization Code", "Implicit"):
        if flow.get("authorizationUrl"):
            cfg["Auth URL"] = flow.get("authorizationUrl")
    if grant_type in ("Authorization Code", "Client Credentials", "Password"):
        if flow.get("tokenUrl"):
            cfg["Token URL"] = flow.get("tokenUrl")
    scopes = _flow_scopes_str(flow)
    if scopes:
        cfg["Scope"] = scopes
    # For Implicit, Response Type is token by default in Kulala
    if grant_type == "Implicit":
        cfg["Response Type"] = "token"
    return cfg


def _build_oauth2_private_config(
    scheme_name: str, scheme: SecurityScheme
) -> dict | None:
    chosen = _choose_oauth2_flow(scheme)
    if not chosen:
        # No resolved flow details; provide secrets-only skeleton
        return {"Client Secret": "CHANGE_ME"}
    grant_type, flow = chosen
    secrets: dict = {}
    # Private-only sensitive placeholders
    if grant_type == "Client Credentials":
        secrets["Client Secret"] = "CHANGE_ME"
    elif grant_type == "Password":
        secrets["Username"] = "CHANGE_ME"
        secrets["Password"] = "CHANGE_ME"
        # Some providers require a client secret for password flow
        secrets["Client Secret"] = "CHANGE_ME"
    elif grant_type == "Authorization Code":
        # Confidential clients often require client secret
        secrets["Client Secret"] = "CHANGE_ME"
    # Implicit: no secrets
    return secrets or None


def generate_env_dicts(model: OpenAPI, env_name: str = "dev") -> tuple[dict, dict]:
    """
    Produce public (http-client.env.json) and private (http-client.private.env.json)
    skeletons for Kulala, based on the model's security schemes.
    Sensitive values are only placed in the private skeleton.
    """
    # Start with pydantic models
    public_env_model = HttpClientEnv()
    private_env_model = HttpClientPrivateEnv()

    public_env_section = EnvSection()
    private_env_section = PrivateEnvSection()

    public_auth: dict[str, dict] = {}
    private_auth: dict[str, dict] = {}

    private_vars: dict[str, Union[str, int, float, dict]] = {}

    comps = getattr(model, "components", None)
    sec_schemes: dict[str, Union[SecurityScheme, Reference]] | None = (
        getattr(comps, "securitySchemes", None) if comps else None
    )

    if sec_schemes:
        for name, scheme in sec_schemes.items():
            # Ignore unresolved references
            if not isinstance(scheme, SecurityScheme3_0) and not isinstance(
                scheme, SecurityScheme3_1
            ):
                continue
            alias = _sanitize(name)
            stype = scheme.type

            if stype == "oauth2":
                pub_cfg = _build_oauth2_public_config(name, scheme)
                prv_cfg = _build_oauth2_private_config(name, scheme)
                # Put all public fields into public env
                if pub_cfg:
                    public_auth[name] = pub_cfg
                # Put only secrets into private env
                if prv_cfg:
                    private_auth[name] = prv_cfg

            elif stype == "openIdConnect":
                # Skip: not represented as OAuth2 in our typed model without discovery values
                pass

            elif stype == "http":
                scheme_name = (scheme.scheme or "").lower()
                if scheme_name == "basic" or scheme_name == "digest":
                    private_vars[f"{alias}_USERNAME"] = "CHANGE_ME"
                    private_vars[f"{alias}_PASSWORD"] = "CHANGE_ME"
                elif scheme_name == "bearer":
                    private_vars[f"{alias}_TOKEN"] = "CHANGE_ME"
                elif scheme_name in ("ntlm", "negotiate"):
                    # No secrets to collect
                    pass
                else:
                    # Unknown http scheme
                    pass

            elif stype == "apiKey":
                private_vars[alias] = "CHANGE_ME"

            elif stype == "mutualTLS":
                # Configure certificates in Kulala config (Lua), not env files
                pass

            else:
                # Unsupported/custom
                pass

    if public_auth:
        typed_public_auth: dict[str, OAuth2Auth] = {}
        for name, cfg in public_auth.items():
            try:
                typed_public_auth[name] = OAuth2Auth(**cfg)
            except Exception:
                # Skip invalid entries
                continue
        if typed_public_auth:
            public_env_section.security = Security(Auth=typed_public_auth)
    if private_auth:
        typed_private_auth: dict[str, PrivateOAuth2Auth] = {}
        for name, cfg in private_auth.items():
            try:
                typed_private_auth[name] = PrivateOAuth2Auth(**cfg)
            except Exception:
                continue
        if typed_private_auth:
            private_env_section.security = PrivateSecurity(Auth=typed_private_auth)

    if private_vars:
        # attach extra vars to private env section
        for k, v in private_vars.items():
            setattr(private_env_section, k, v)

    # Attach the environment section under the env name
    setattr(
        public_env_model,
        env_name,
        public_env_section.model_dump(by_alias=True, exclude_none=True),
    )
    setattr(
        private_env_model,
        env_name,
        private_env_section.model_dump(by_alias=True, exclude_none=True),
    )

    # Dump to dicts preserving aliases and excluding None
    return (
        public_env_model.model_dump(by_alias=True, exclude_none=True),
        private_env_model.model_dump(by_alias=True, exclude_none=True),
    )
