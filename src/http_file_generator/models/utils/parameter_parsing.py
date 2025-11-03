import re
from typing import Union
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
                raise TypeError("Expected Parameter-like object, got {}".format(type(param)))
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
    """
    # find the param in the path
    token = "{" + param.name + "}"
    new_name = param.name
    if token in path:
        # replace the param token with a templated variable
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
    if "?" in path:
        path += "\n&" + param.name + "={{" + param.name + "}}"
    else:
        path += "\n?" + param.name + "={{" + param.name + "}}"
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
    pass
    # raise NotImplementedError


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
    return HttpVariable(
        name=param.name,
        value=str(value) or "",
        description=param.description or "",
    )


def handle_missing_path_parasm(path: str) -> tuple[str, list[HttpVariable]]:
    params = []
    if re_params := re.search(r"(?<!\{)\{([^}]+)\}(?!\})", path):
        # find the param in the path
        # param_name = re.search(r"{(.+?)}", path).group(1)
        for param_name in re_params.groups():
            # param_name = param_name.group(1)
            new_name = param_name
            placeholder = "{" + param_name + "}"
            if placeholder in path:
                # ensure placeholder remains single-braced
                path = path.replace(placeholder, "{" + new_name + "}")
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
