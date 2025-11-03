from typing import Dict, List, Tuple, Union

from openapi_pydantic.v3.v3_0 import SecurityScheme as SecurityScheme3_0
from openapi_pydantic.v3.v3_1 import SecurityScheme as SecurityScheme3_1
from openapi_pydantic.v3.v3_0 import Operation as Operation3_0
from openapi_pydantic.v3.v3_1 import Operation as Operation3_1

from ..http_file.var import HttpVariable

SecurityScheme = Union[SecurityScheme3_0, SecurityScheme3_1]
Operation = Union[Operation3_0, Operation3_1]


def _sanitize(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name).upper()


def _append_query_param(path: str, name: str, var_name: str) -> str:
    placeholder = "{{" + var_name + "}}"
    if "?" in path:
        return path + f"\n&{name}=" + placeholder
    return path + f"\n?{name}=" + placeholder


def _choose_effective_security(
    operation: Operation, root_security: List[dict] | None
) -> List[dict]:
    # None => inherit, [] => disable
    if operation.security is None:
        return root_security or []
    return operation.security


def apply_security(
    path: str,
    headers: Dict[str, str] | None,
    params: List[HttpVariable] | None,
    operation: Operation,
    root_security: List[dict] | None,
    security_schemes: Dict[str, SecurityScheme] | None,
) -> Tuple[str, Dict[str, str], List[HttpVariable]]:
    """
    Apply OpenAPI security requirements to the request by mutating path, headers and params.

    - Chooses the first alternative from the security requirement list (OR semantics)
    - Applies all schemes within the chosen alternative (AND semantics)
    - Uses Kulala conventions for HTTP file generation
    """
    if not security_schemes:
        return path, headers or {}, params or []

    effective = _choose_effective_security(operation, root_security)
    if not effective:
        return path, headers or {}, params or []

    # Choose the first alternative
    first_alt = effective[0]
    if not isinstance(first_alt, dict):
        return path, headers or {}, params or []

    # Work on a copy of headers
    out_headers: Dict[str, str] = dict(headers or {})
    out_params: List[HttpVariable] = list(params or [])

    for scheme_name, _scopes in first_alt.items():
        scheme = security_schemes.get(scheme_name) if security_schemes else None
        if not scheme:
            continue

        alias_upper = _sanitize(scheme_name)

        if scheme.type == "http":
            http_scheme = (scheme.scheme or "").lower()
            if http_scheme == "basic":
                # Authorization: Basic {{ALIAS_USERNAME}}:{{ALIAS_PASSWORD}}
                user_var = f"{alias_upper}_USERNAME"
                pass_var = f"{alias_upper}_PASSWORD"
                out_headers["Authorization"] = (
                    "Basic " + ("{{" + user_var + "}}") + ":" + ("{{" + pass_var + "}}")
                )
            elif http_scheme == "bearer":
                # plain bearer token variable
                token_var = f"{alias_upper}_TOKEN"
                out_headers["Authorization"] = "Bearer " + ("{{" + token_var + "}}")
            elif http_scheme == "digest":
                user_var = f"{alias_upper}_USERNAME"
                pass_var = f"{alias_upper}_PASSWORD"
                out_headers["Authorization"] = (
                    "Digest " + ("{{" + user_var + "}}") + ":" + ("{{" + pass_var + "}}")
                )
            elif http_scheme == "ntlm":
                out_headers["Authorization"] = "NTLM"
            elif http_scheme == "negotiate":
                out_headers["Authorization"] = "Negotiate"
            else:
                # Unknown http scheme
                pass

        elif scheme.type == "apiKey":
            name = scheme.name or "api_key"
            var_name = _sanitize(scheme_name)
            location = (scheme.security_scheme_in or "header").lower()
            if location == "header":
                out_headers[name] = f"{{{{{var_name}}}}}"
            elif location == "query":
                path = _append_query_param(path, name, var_name)
            elif location == "cookie":
                cookie_val = f"{name}=" + ("{{" + var_name + "}}")
                if "Cookie" in out_headers and out_headers["Cookie"]:
                    out_headers["Cookie"] = out_headers["Cookie"] + "; " + cookie_val
                else:
                    out_headers["Cookie"] = cookie_val

        elif scheme.type in ("oauth2", "openIdConnect"):
            # Delegate OAuth2/OpenID Connect to Kulala auth manager via $auth.token
            # Need to escape braces in f-string to output {{ ... }} literally
            out_headers["Authorization"] = (
                f'Bearer {{{{$auth.token("{scheme_name}")}}}}'
            )

        elif scheme.type == "mutualTLS":
            # Configured via client certificates; nothing to add in request
            pass

        else:
            # Unsupported type
            pass

    return path, out_headers, out_params
