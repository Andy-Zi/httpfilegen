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

def handle_params(path: str, parameters: list[Parameter]) -> tuple[str, list[HttpVariable]]:
    """
    Handle parameters in the request path.
    """
    params = []
    if parameters:
        for param in parameters:
            if not isinstance(param, Parameter):
                raise TypeError("Expected Parameter, got {}".format(type(param)))
            match param.param_in:
                case loc if loc.value == "query":
                    path, param = handle_query_params(path, param)
                    if param:
                        params.append(param)
                case loc if loc.value == "header":
                    param = handle_header_params(path, param)
                    if param:
                        params.append(param)
                case loc if loc.value == "path":
                    path, param = handle_path_params(path, param)
                    if param:
                        params.append(param)
                case loc if loc.value == "cookie":
                    param = handle_cookie_params(path, param)
                    if param:
                        params.append(param)
                case _:
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
    param_name = "{" + param.name + "}"
    new_name = param.name
    if param_name in path:
        # replace the param with a sample value
        path = path.replace(param_name, "{{" + new_name + "}}")
    else:
        raise ValueError(f"Parameter {param.name} not found in path {path}")
    if param.example:
        value = param.example
    elif param.examples:
        value = next(iter(param.examples.values()))
    elif param.param_schema:
        value = (
            _generate_sample_param_from_schema(
                param.param_schema.dict(by_alias=True, exclude_none=True)
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
    if '?' in path:
        path += "&" + param.name + "={{" + param.name + "}}"
    else:
        path += "?" + param.name + "={{" + param.name + "}}"
    if param.example:
        value = param.example
    elif param.examples:
        value = next(iter(param.examples.values()))
    elif param.param_schema:
        value = (
            _generate_sample_param_from_schema(
                param.param_schema.dict(by_alias=True, exclude_none=True)
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


def handle_header_params(path: str, param: Parameter) -> str:
    """
    Handle header parameters in the request.
    """
    pass
    # raise NotImplementedError


def handle_cookie_params(path: str, param: Parameter) -> str:
    """
    Handle cookie parameters in the request.
    """
    pass
    # raise NotImplementedError


def handle_missing_path_parasm(path: str) -> tuple[str, list[HttpVariable]]:
    params = []
    if re_params := re.search(r"(?<!\{)\{([^}]+)\}(?!\})", path):
        # find the param in the path
        # param_name = re.search(r"{(.+?)}", path).group(1)
        for param_name in re_params.groups():
            # param_name = param_name.group(1)
            new_name = param_name
            if param_name in path:
                # replace the param with a sample value
                path = path.replace(param_name, "{" + new_name + "}")
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
