import json
from typing import Literal
from openapi_pydantic import Operation, RequestBody, Parameter, MediaType
from openapi_pydantic.v3.v3_1.parameter import ParameterLocation
from openapi_pydantic.v3.v3_1.example import Example
from pydantic import BaseModel, Field
from jsf import JSF

from .scripts import HttpScript

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
    params: dict[str, str] | None = Field(
        default_factory=dict, description="Parameters for the request as key-value pairs"
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
                [f"###   {line}" for line in self.description.splitlines()]
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

    def to_http_file(self, base_url: str) -> str:
        lines = ""
        lines += self._frontmatter()
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
                    body = cls._generate_sample_from_schema( content_item.media_type_schema.dict(by_alias=True, exclude_none=True)) or {}
                else:
                    body = {}
                    media_type = None
                headers = {"Content-Type": media_type} if media_type else {}

        # Handle header parameters
        if operation.parameters:
            params = {}
            for param in operation.parameters:
                if not isinstance(param, Parameter):
                    raise TypeError("Expected Parameter, got {}".format(type(param)))
                match param.param_in:
                    case ParameterLocation.QUERY:
                        params[param.name] = cls.handle_query_params(path, param)
                    case ParameterLocation.HEADER:
                        params[param.name] = cls.handle_header_params(path, param)
                    case ParameterLocation.PATH:
                        path, params[param.name] = cls.handle_path_params(path, param)
                    case ParameterLocation.COOKIE:
                        params[param.name] = cls.handle_cookie_params(path, param)

        return cls(
            method=method,
            path=path,
            headers=headers,
            body=body,
            description=operation.description,
            summary=operation.summary,
        )

    def handle_path_params(self, path: str, param: Parameter) -> tuple[str, str]:
        """
        Handle path parameters in the request path.
        """
        raise NotImplementedError

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
    def _generate_sample_from_schema(cls, schema: dict) -> dict:
        """Generate a sample dict conforming to the given JSON schema using jsf."""
        try:
            faker = JSF(schema=schema)
            sample = faker.generate(n=1,use_defaults=True,use_examples=True)
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
