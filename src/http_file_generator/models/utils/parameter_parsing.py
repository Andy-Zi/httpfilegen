import re
from typing import Union
from urllib.parse import quote
from openapi_pydantic.v3.v3_1 import (
    Parameter as Parameter3_1,
    RequestBody as RequestBody3_1,
    ParameterLocation as ParameterLocation3_1,
    Operation as Operation3_1,
)
from openapi_pydantic.v3.v3_0 import (
    Parameter as Parameter3_0,
    RequestBody as RequestBody3_0,
    ParameterLocation as ParameterLocation3_0,
    Operation as Operation3_0,
)
from jsf import JSF


from ..http_file.var import HttpVariable


def _encode_query_param_name(name: str) -> str:
    """URL-encode a query parameter name, preserving safe characters."""
    # Encode special characters in parameter names
    # safe="" means encode everything except alphanumerics and _.-~
    return quote(name, safe="_.-~")

Parameter = Union[Parameter3_0, Parameter3_1]
RequestBody = Union[RequestBody3_0, RequestBody3_1]
ParameterLocation = Union[ParameterLocation3_0, ParameterLocation3_1]
Operation = Union[Operation3_0, Operation3_1]


def handle_params(
    path: str, parameters: list[Parameter]
) -> tuple[str, list[HttpVariable]]:
    """
    Handle parameters in the request path.
    """
    params = []
    if parameters:
        for param in parameters:
            # Accept duck-typed parameter-like objects used in tests/resolved refs
            if not hasattr(param, "name") or not hasattr(param, "param_in"):
                raise TypeError(
                    "Expected Parameter-like object, got {}".format(type(param))
                )
            loc = param.param_in
            loc_value = getattr(loc, "value", loc)
            if loc_value == "query":
                path, hv = handle_query_params(path, param)
                if hv:
                    params.append(hv)
            elif loc_value == "header":
                hv = handle_header_params(path, param)
                if hv:
                    params.append(hv)
            elif loc_value == "path":
                path, hv = handle_path_params(path, param)
                if hv:
                    params.append(hv)
            elif loc_value == "cookie":
                hv = handle_cookie_params(path, param)
                if hv:
                    params.append(hv)
            else:
                raise NotImplementedError(
                    f"Parameter location {param.param_in} is not supported"
                )
    path, missing_params = handle_missing_path_parasm(path)
    if missing_params:
        params.extend(missing_params)
    return path, params


def handle_path_params(path: str, param: Parameter) -> tuple[str, HttpVariable]:
    """
    Handle path parameters in the request path.

    Converts OpenAPI path parameter syntax to HTTP client template variable syntax:
    - OpenAPI uses single braces: /users/{id}
    - HTTP clients (IntelliJ, Kulala, httpyac) use double braces: /users/{{id}}

    This conversion allows the generated .http file to use environment variables
    that can be defined in http-client.env.json files.
    """
    # OpenAPI path parameter token uses single braces
    token = "{" + param.name + "}"
    new_name = param.name
    if token in path:
        # Convert to double braces for HTTP client template variable syntax
        path = path.replace(token, "{{" + new_name + "}}")
    else:
        raise ValueError(f"Parameter {param.name} not found in path {path}")
    if param.example:
        value = param.example
    elif param.examples:
        ex = next(iter(param.examples.values()))
        value = getattr(ex, "value", ex)
    elif param.param_schema:
        value = (
            _generate_sample_param_from_schema(
                param.param_schema.model_dump(by_alias=True, exclude_none=True)
            )
            or {}
        )
    else:
        value = {}
    return path, HttpVariable(
        name=param.name,
        value=str(value) or "",
        description=param.description or "",
    )


def _generate_sample_body_from_schema(schema: dict) -> dict:
    """Generate a sample dict conforming to the given JSON schema using jsf."""
    try:
        faker = JSF(schema=schema, allow_none_optionals=0)
        sample = faker.generate(n=1, use_defaults=True, use_examples=True)
        if isinstance(sample, list):
            if sample:
                return sample[0]
            else:
                return {}
        elif not isinstance(sample, dict):
            return {}
        return sample
    except Exception as e:
        raise ValueError(f"Failed to generate sample from schema: {e}")


def _generate_sample_param_from_schema(schema: dict) -> Union[int, str, float, bool]:
    """Generate a sample dict conforming to the given JSON schema using jsf."""
    try:
        faker = JSF(schema=schema)
        sample = faker.generate(n=1, use_defaults=True, use_examples=True)
        if isinstance(sample, list):
            if sample:
                return sample[0]
            else:
                return ""
        if not isinstance(sample, (int, str, float, bool)):
            try:
                return str(sample)
            except TypeError:
                return ""
        return sample
    except Exception as e:
        raise ValueError(f"Failed to generate sample from schema: {e}")


def handle_query_params(path: str, param: Parameter) -> tuple[str, HttpVariable]:
    """
    Handle query parameters in the request path.
    """
    # URL-encode the parameter name for the query string
    encoded_name = _encode_query_param_name(param.name)
    if "?" in path:
        path += "\n&" + encoded_name + "={{" + param.name + "}}"
    else:
        path += "\n?" + encoded_name + "={{" + param.name + "}}"
    if param.example:
        value = param.example
    elif param.examples:
        ex = next(iter(param.examples.values()))
        value = getattr(ex, "value", ex)
    elif param.param_schema:
        value = (
            _generate_sample_param_from_schema(
                param.param_schema.model_dump(by_alias=True, exclude_none=True)
            )
            or {}
        )
    else:
        value = {}
    return path, HttpVariable(
        name=param.name,
        value=str(value) or "",
        description=param.description or "",
    )


def handle_header_params(path: str, param: Parameter) -> HttpVariable | None:
    """
    Handle header parameters by creating a variable placeholder.
    The actual header line can be added manually by the user using the variable.
    """
    if param.example:
        value = param.example
    elif param.examples:
        ex = next(iter(param.examples.values()))
        value = getattr(ex, "value", ex)
    elif param.param_schema:
        value = (
            _generate_sample_param_from_schema(
                param.param_schema.model_dump(by_alias=True, exclude_none=True)
            )
            or {}
        )
    else:
        value = {}
    return HttpVariable(
        name=param.name,
        value=str(value) or "",
        description=param.description or "",
    )


def handle_cookie_params(path: str, param: Parameter) -> HttpVariable | None:
    """
    Handle cookie parameters by creating a variable placeholder.
    """
    if param.example:
        value = param.example
    elif param.examples:
        ex = next(iter(param.examples.values()))
        value = getattr(ex, "value", ex)
    elif param.param_schema:
        value = (
            _generate_sample_param_from_schema(
                param.param_schema.model_dump(by_alias=True, exclude_none=True)
            )
            or {}
        )
    else:
        value = {}
    if param.description:
        desc = param.description.strip()
    else:
        desc = ""
    return HttpVariable(name=param.name, value=str(value) or "", description=desc)


def handle_missing_path_parasm(path: str) -> tuple[str, list[HttpVariable]]:
    """
    Find path parameters that weren't declared in the OpenAPI parameters list.

    Some specs define path segments like /users/{id} without a corresponding
    parameter definition. This function detects those and creates placeholder
    HttpVariables for them.

    Returns:
        tuple: Updated path (unchanged for missing params) and list of placeholder variables.
    """
    params = []
    # Regex explanation: Match single-braced tokens like {param} but NOT double-braced {{param}}
    #
    # (?<!\{)     - Negative lookbehind: not preceded by '{'
    # \{          - Literal opening brace
    # ([^}]+)     - Capture group: one or more chars that aren't '}'
    # \}          - Literal closing brace
    # (?!\})      - Negative lookahead: not followed by '}'
    #
    # This distinguishes OpenAPI path params {id} from HTTP client template vars {{id}}
    # Use findall() to find ALL undeclared parameters, not just the first one
    param_names = re.findall(r"(?<!\{)\{([^}]+)\}(?!\})", path)
    for param_name in param_names:
        placeholder = "{" + param_name + "}"
        if placeholder in path:
            # Keep as single braces - these are undeclared params that need
            # to be manually replaced. The path will need user intervention.
            path = path.replace(placeholder, "{" + param_name + "}")
        else:
            raise ValueError(f"Parameter {param_name} not found in path {path}")

        params.append(
            HttpVariable(
                name=param_name,
                value="",
                description="",
            )
        )
    return path, params
