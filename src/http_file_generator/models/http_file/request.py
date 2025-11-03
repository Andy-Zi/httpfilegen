import json
from typing import Union, Any
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
from openapi_pydantic.v3.v3_1 import SecurityScheme as SecurityScheme3_1
from openapi_pydantic.v3.v3_0 import SecurityScheme as SecurityScheme3_0
from openapi_pydantic.v3.v3_1 import Reference as Reference3_1
from openapi_pydantic.v3.v3_0 import Reference as Reference3_0
from pydantic import BaseModel, Field
from jsf import JSF

from http_file_generator.models.utils.body_parsing import handle_body
from http_file_generator.models.utils.parameter_parsing import handle_params
from http_file_generator.models.utils.auth_parsing import apply_security

from ..enums import METHOD

from .scripts import HttpScript
from .var import HttpVariable

Parameter = Union[Parameter3_0, Parameter3_1]
RequestBody = Union[RequestBody3_0, RequestBody3_1]
ParameterLocation = Union[ParameterLocation3_0, ParameterLocation3_1]
Operation = Union[Operation3_0, Operation3_1]
SecurityScheme = Union[SecurityScheme3_0, SecurityScheme3_1]
Reference = Union[Reference3_0, Reference3_1]

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
    # Collected response examples (all statuses/content-types) for this operation
    response_examples: list[dict[str, Any]] | None = Field(
        default=None,
        description=(
            "List of example entries: {status, content_type, name?, value}."
        ),
    )
    # Collected request body examples (all content-types) for this operation
    request_examples: list[dict[str, Any]] | None = Field(
        default=None,
        description=(
            "List of request examples: {content_type, name?, value}."
        ),
    )

    def _frontmatter(self):
        lines = ""
        lines += SEPARATOR
        lines += f"### Request: {self.method} {self.path.replace('\n', '')}\n"
        if self.summary:
            lines += (
                f"### Summary: {self.summary.rstrip('\n') or 'No summary provided'}\n"
            )
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

    def to_http_file(
        self,
        base_url: str,
        include_examples: bool = False,
        include_schema: bool = False,
    ) -> str:
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
        # Append commented request body examples if enabled
        if include_schema and self.request_examples:
            lines += "\n### Request Examples\n"
            lines += self._render_request_examples(self.request_examples)
        # Append commented response examples if enabled
        if include_examples and self.response_examples:
            lines += "\n### Response Examples\n"
            lines += self._render_response_examples(self.response_examples)
        return lines

    @classmethod
    def from_operation(
        cls,
        method: METHOD,
        path: str,
        operation: Operation,
        root_security: list[dict] | None = None,
        security_schemes: dict[str, Union[SecurityScheme, Reference]] | None = None,
    ) -> "HttpRequest":
        """
        Create an HttpRequest object from an OpenAPI operation object.
        """
        # Handle request body
        bodies = handle_body(path, operation.requestBody)
        (body, headers) = list(bodies.values())[0] if bodies else (None, None)

        # Handle parameters
        path, params = handle_params(path, operation.parameters)

        # Apply security requirements (OpenAPI security + Kulala semantics)
        path, headers, params = apply_security(
            path=path,
            headers=headers or {},
            params=params or [],
            operation=operation,
            root_security=root_security,
            security_schemes=security_schemes,  # type: ignore[arg-type]
        )

        # Collect request/response examples for this operation
        request_examples = cls._collect_request_examples(operation)
        # Collect response examples for this operation (all statuses/content types)
        response_examples = cls._collect_response_examples(operation)

        return cls(
            body=body,
            description=operation.description,
            headers=headers,
            method=method,
            params=params,
            path=path,
            summary=operation.summary,
            request_examples=request_examples or None,
            response_examples=response_examples or None,
        )

    @staticmethod
    def _generate_sample_from_schema(schema: dict) -> Any:
        try:
            faker = JSF(schema=schema)
            sample = faker.generate()
            return sample
        except Exception:
            return None

    @classmethod
    def _collect_response_examples(cls, operation: Operation) -> list[dict[str, Any]]:
        examples: list[dict[str, Any]] = []
        responses = getattr(operation, "responses", None) or {}
        for status, response in responses.items():
            content_map = getattr(response, "content", None) or {}
            if not content_map:
                # No content provided for this status; include a placeholder block
                examples.append(
                    {
                        "status": status,
                        "content_type": None,
                        "name": None,
                        "value": None,
                    }
                )
                continue
            for content_type, media in content_map.items():
                # Single anonymous example
                example_val = getattr(media, "example", None)
                if example_val is not None:
                    examples.append(
                        {
                            "status": status,
                            "content_type": content_type,
                            "name": None,
                            "value": example_val,
                        }
                    )
                    continue
                # Named examples
                ex_map = getattr(media, "examples", None)
                if ex_map:
                    for ex_name, ex_obj in ex_map.items():
                        val = getattr(ex_obj, "value", ex_obj)
                        examples.append(
                            {
                                "status": status,
                                "content_type": content_type,
                                "name": ex_name,
                                "value": val,
                            }
                        )
                    continue
                # Fallback to schema-based sample
                schema = getattr(media, "media_type_schema", None)
                if schema is not None:
                    schema_dict = schema.model_dump(by_alias=True, exclude_none=True)
                    if schema_dict:
                        val = cls._generate_sample_from_schema(schema_dict)
                        examples.append(
                            {
                                "status": status,
                                "content_type": content_type,
                                "name": None,
                                "value": val,
                            }
                        )
                else:
                    examples.append(
                        {
                            "status": status,
                            "content_type": content_type,
                            "name": None,
                            "value": None,
                        }
                    )
        return examples

    @staticmethod
    def _render_response_examples(examples: list[dict[str, Any]]) -> str:
        lines = "\n"
        for ex in examples:
            status = ex.get("status")
            ctype = ex.get("content_type")
            name = ex.get("name")
            header = f"## Response example ({status}"
            if ctype:
                header += f" {ctype}"
            if name:
                header += f" - {name}"
            header += ")\n"
            lines += header
            value = ex.get("value")
            if value is None:
                lines += "# <no example available>\n\n"
                continue
            if isinstance(value, (dict, list)):
                body = json.dumps(value, indent=2)
            elif isinstance(value, (int, float, bool)):
                body = json.dumps(value)
            else:
                body = str(value)
            for ln in body.splitlines():
                lines += f"# {ln}\n"
            lines += "\n"
        return lines

    @classmethod
    def _collect_request_examples(cls, operation: Operation) -> list[dict[str, Any]]:
        examples: list[dict[str, Any]] = []
        rb = getattr(operation, "requestBody", None)
        if not rb:
            return examples
        content_map = getattr(rb, "content", None) or {}
        for content_type, media in content_map.items():
            # Single anonymous example
            example_val = getattr(media, "example", None)
            if example_val is not None:
                examples.append(
                    {"content_type": content_type, "name": None, "value": example_val}
                )
                continue
            # Named examples
            ex_map = getattr(media, "examples", None)
            if ex_map:
                for ex_name, ex_obj in ex_map.items():
                    val = getattr(ex_obj, "value", ex_obj)
                    examples.append(
                        {"content_type": content_type, "name": ex_name, "value": val}
                    )
                continue
            # Fallback to schema-based sample
            schema = getattr(media, "media_type_schema", None)
            if schema is not None:
                schema_dict = schema.model_dump(by_alias=True, exclude_none=True)
                if schema_dict:
                    val = cls._generate_sample_from_schema(schema_dict)
                    examples.append(
                        {"content_type": content_type, "name": None, "value": val}
                    )
            else:
                examples.append(
                    {"content_type": content_type, "name": None, "value": None}
                )
        return examples

    @staticmethod
    def _render_request_examples(examples: list[dict[str, Any]]) -> str:
        lines = "\n"
        for ex in examples:
            ctype = ex.get("content_type")
            name = ex.get("name")
            header = "## Request example ("
            if ctype:
                header += f"{ctype}"
            if name:
                header += f" - {name}"
            header += ")\n"
            lines += header
            value = ex.get("value")
            if value is None:
                lines += "# <no example available>\n\n"
                continue
            if isinstance(value, (dict, list)):
                body = json.dumps(value, indent=2)
            elif isinstance(value, (int, float, bool)):
                body = json.dumps(value)
            else:
                body = str(value)
            for ln in body.splitlines():
                lines += f"# {ln}\n"
            lines += "\n"
        return lines
