import json
from typing import Literal
from openapi_pydantic import Operation, RequestBody, Parameter
from openapi_pydantic.v3.v3_1.parameter import ParameterLocation
from openapi_pydantic.v3.v3_1.example import Example
from pydantic import BaseModel, Field

from .scripts import HttpScript

METHODS = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]


class HttpRequest(BaseModel):
    method: METHODS = Field(..., description="HTTP method, e.g., GET, POST")
    path: str = Field(..., description="Request URL")
    headers: dict[str, str] | None = Field(
        default_factory=dict, description="Headers as key-value pairs"
    )
    body: dict | None = Field(None, description="Request body as JSON dict")
    pre_script: HttpScript | None = Field(
        None, description="Script to run before request"
    )
    post_script: HttpScript | None = Field(
        None, description="Script to run after request"
    )

    def to_http_file(self, base_url: str) -> str:
        lines = [f"{self.method} {base_url}{self.path}"]
        if self.headers:
            lines.extend(f"{k}: {v}" for k, v in self.headers.items())
        lines.append("")  # Empty line before body
        if self.body:
            lines.append(json.dumps(self.body, indent=2))
        return "\n".join(lines)

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
                if "application/json" in content:
                    media = content["application/json"]
                    if media.example:
                        body = media.example
                    elif media.examples:
                        first_key = next(iter(media.examples))
                        ex = media.examples[first_key]
                        if isinstance(ex, Example) and ex.value:
                            body = ex.value

        # Handle header parameters
        if operation.parameters:
            for param in operation.parameters:
                if isinstance(param, Parameter):
                    if param.param_in == ParameterLocation.HEADER:
                        if param.example:
                            headers[param.name] = str(param.example)
                        elif param.examples:
                            first_key = next(iter(param.examples))
                            ex = param.examples[first_key]
                            if isinstance(ex, Example) and ex.value:
                                headers[param.name] = str(ex.value)

        return cls(method=method, path=path, headers=headers, body=body)
