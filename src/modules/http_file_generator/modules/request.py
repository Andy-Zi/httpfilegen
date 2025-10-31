import json
from typing import Any, Literal, Union
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
from pydantic import BaseModel, Field
from jsf import JSF

from .scripts import HttpScript
from .var import HttpVariable

Parameter = Union[Parameter3_0, Parameter3_1]
RequestBody = Union[RequestBody3_0, RequestBody3_1]
ParameterLocation = Union[ParameterLocation3_0, ParameterLocation3_1]
Operation = Union[Operation3_0, Operation3_1]

METHODS = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]

SEPARATOR = "#" * 53 + "\n"


class HttpRequest(BaseModel):
    method: METHODS = Field(..., description="HTTP method, e.g., GET, POST")
    path: str = Field(..., description="Request URL")
    headers: dict[str, str] | None = Field(
        default_factory=dict, description="Headers as key-value pairs"
    )
    body: dict | None = Field(None, description="Request body as JSON dict")
    summary: str | None = Field(None, description="Short summary of the request")
    description: str | None = Field(None, description="Detailed description")
    params: list[HttpVariable] | None = Field(
        default_factory=dict,
        description="Parameters for the request as key-value pairs",
    )
    pre_script: HttpScript | None = Field(
        None, description="Script to run before request"
    )
    post_script: HttpScript | None = Field(
        None, description="Script to run after request"
    )

    def _frontmatter(self):
        lines = ""
        lines += SEPARATOR
        lines += f"### Request: {self.method} {self.path}\n"
        lines += f"### Summary: {self.summary or 'No summary provided'}\n"
        if self.description and "\n" in self.description:
            desc = "\n" + "\n".join(
                [f"###   {line}".rstrip() for line in self.description.splitlines()]
            )
        else:
            desc = self.description
        lines += f"### Description: {desc or 'No description provided'}\n"
        lines += SEPARATOR
        lines += "\n\n"
        return lines

    def _body(self):
        lines = ""
        if self.body:
            lines += json.dumps(self.body, indent=4)
            lines += "\n"
        return lines

    def _params(self):
        lines = ""
        if not self.params:
            return lines
        for param in self.params:
            lines += f"{str(param)}\n"
        return lines

    def to_http_file(self, base_url: str) -> str:
        lines = ""
        lines += self._frontmatter()
        lines += self._params()
        lines += f"{self.method} {base_url}{self.path}\n"
        if self.headers:
            for k, v in self.headers.items():
                lines += f"{k}: {v}\n"
        lines += "\n"
        if self.body:
            lines += json.dumps(self.body, indent=4)
        return lines

    @classmethod
    def from_operation(
        cls, method: METHODS, path: str, operation: Operation
    ) -> "HttpRequest":
        """
        Create an HttpRequest object from an OpenAPI operation object.
        """
        headers = {}
        body = None

        # Handle request body
        if operation.requestBody:
            if isinstance(operation.requestBody, RequestBody):
                content = operation.requestBody.content
                if len(content) > 1:
                    raise NotImplementedError(
                        "Multiple content types are not supported yet. Please specify only one content type."
                    )
                media_type, content_item = next(
                    iter(operation.requestBody.content.items())
                )
                if content_item.example:
                    body = content_item.example
                elif content_item.examples:
                    body = next(iter(content_item.examples.values()))
                elif content_item.media_type_schema:
                    body = (
                        cls._generate_sample_body_from_schema(
                            content_item.media_type_schema.dict(
                                by_alias=True, exclude_none=True
                            )
                        )
                        or {}
                    )
                else:
                    body = {}
                    media_type = None
                headers = {"Content-Type": media_type} if media_type else {}

        # Handle header parameters
        params = []
        if operation.parameters:
            for param in operation.parameters:
                if not isinstance(param, Parameter):
                    raise TypeError("Expected Parameter, got {}".format(type(param)))
                match param.param_in:
                    case loc if loc.value == "query":
                        pass
                        # params[param.name] = cls.handle_query_params(path, param)
                    case loc if loc.value == "header":
                        pass
                        # params[param.name] = cls.handle_header_params(path, param)
                    case loc if loc.value == "path":
                        # path, params[param.name] = cls.handle_path_params(cls, path, param)
                        path, param = cls.handle_path_params(cls, path, param)
                        params.append(param)
                    case loc if loc.value == "cookie":
                        pass
                        # params[param.name] = cls.handle_cookie_params(path, param)
                    case _:
                        raise NotImplementedError(
                            f"Parameter location {param.param_in} is not supported"
                        )

        return cls(
            body=body,
            description=operation.description,
            headers=headers,
            method=method,
            params=params,
            path=path,
            summary=operation.summary,
        )

    def handle_path_params(
        self, path: str, param: Parameter
    ) -> tuple[str, HttpVariable]:
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
                self._generate_sample_param_from_schema(
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

    def handle_query_params(self, path: str, param: Parameter) -> str:
        """
        Handle query parameters in the request path.
        """
        raise NotImplementedError

    def handle_header_params(self, path: str, param: Parameter) -> str:
        """
        Handle header parameters in the request.
        """
        raise NotImplementedError

    def handle_cookie_params(self, path: str, param: Parameter) -> str:
        """
        Handle cookie parameters in the request.
        """
        raise NotImplementedError

    @classmethod
    def _generate_sample_body_from_schema(cls, schema: dict) -> dict:
        """Generate a sample dict conforming to the given JSON schema using jsf."""
        try:
            faker = JSF(
                schema=schema,
                allow_none_optionals=0
            )
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

    @classmethod
    def _generate_sample_param_from_schema(cls, schema: dict) -> Union[int, str, float, bool]:
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
