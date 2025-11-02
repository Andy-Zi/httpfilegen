import json
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
from pydantic import BaseModel, Field

from http_file_generator.models.utils.body_parsing import handle_body
from http_file_generator.models.utils.parameter_parsing import handle_params

from ..enums import METHOD

from .scripts import HttpScript
from .var import HttpVariable

Parameter = Union[Parameter3_0, Parameter3_1]
RequestBody = Union[RequestBody3_0, RequestBody3_1]
ParameterLocation = Union[ParameterLocation3_0, ParameterLocation3_1]
Operation = Union[Operation3_0, Operation3_1]

SEPARATOR = "#" * 53 + "\n"


class HttpRequest(BaseModel):
    method: METHOD = Field(..., description="HTTP method, e.g., GET, POST")
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
        lines += f"### Request: {self.method} {self.path.replace("\n","")}\n"
        if self.summary:
            lines += f"### Summary: {self.summary.rstrip("\n") or 'No summary provided'}\n"
        if self.description:
            lines = ""
            if self.description:
                if "\n" in self.description:
                    desc = "\n" + "\n".join(
                        [f"###  {line}".rstrip() for line in self.description.splitlines()]
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
        cls, method: METHOD, path: str, operation: Operation
    ) -> "HttpRequest":
        """
        Create an HttpRequest object from an OpenAPI operation object.
        """
        # Handle request body
        bodies = handle_body(path, operation.requestBody)
        
        (body, headers) = list(bodies.values())[0] if bodies else (None, None)

        # Handle parameters
        path, params = handle_params(path, operation.parameters)

        return cls(
            body=body,
            description=operation.description,
            headers=headers,
            method=method,
            params=params,
            path=path,
            summary=operation.summary,
        )
