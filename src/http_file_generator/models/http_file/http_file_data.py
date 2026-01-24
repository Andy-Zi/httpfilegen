from typing import Union
from openapi_pydantic import PathItem
from openapi_pydantic.v3.v3_0 import Server as Server3_0
from openapi_pydantic.v3.v3_1 import Server as Server3_1
from openapi_pydantic.v3.v3_0 import SecurityScheme as SecurityScheme3_0
from openapi_pydantic.v3.v3_1 import SecurityScheme as SecurityScheme3_1
from openapi_pydantic.v3.v3_0 import Reference as Reference3_0
from openapi_pydantic.v3.v3_1 import Reference as Reference3_1
from pydantic import BaseModel, Field

from .request import HttpRequest
from ..enums import METHOD
from .var import BaseURL
from ..settings.settings import EditorMode

Server = Union[Server3_0, Server3_1]
SecurityScheme = Union[SecurityScheme3_0, SecurityScheme3_1]
Reference = Union[Reference3_0, Reference3_1]


class HttpFileData(BaseModel):
    base_urls: set[BaseURL] = Field(..., description="Base URL for all requests")
    # auth: str | None = Field(None, description="Authorization header value")
    requests: list[HttpRequest] = Field(..., description="List of HTTP requests")

    @classmethod
    def from_paths(
        cls,
        server: list[Server],
        paths: dict[str, PathItem],
        root_security: list[dict] | None = None,
        security_schemes: dict[str, Union[SecurityScheme, Reference]] | None = None,
    ) -> "HttpFileData":
        """
        Convert a paths object to a list of HTTP requests
        """
        requests = []
        for path, path_item in paths.items():
            for method in path_item.model_dump(exclude_none=True):
                if method.upper() in METHOD:
                    operation = getattr(path_item, method)
                    if operation:
                        request = HttpRequest.from_operation(
                            path=path,
                            method=method.upper(),
                            operation=operation,
                            root_security=root_security,  # type: ignore[arg-type]
                            security_schemes=security_schemes,  # type: ignore[arg-type]
                        )
                        requests.append(request)
        base_urls = set()
        for srv in server:
            # Skip invalid server URLs (empty, "/", or whitespace-only)
            url = srv.url.strip() if srv.url else ""
            if not url or url == "/":
                continue
            base_urls.add(
                BaseURL(value=srv.url, description=srv.description or "")
            )

        return cls(
            base_urls=base_urls,
            requests=requests,
        )

    def to_http_file(
        self,
        include_examples: bool = False,
        include_schema: bool = False,
        editor_mode: EditorMode = EditorMode.DEFAULT,
    ) -> str:
        """
        Convert the data to an HTTP file string
        """
        parts = []

        # Add editor-specific header
        header = self._get_editor_header(editor_mode)
        if header:
            parts.append(header)

        # requests
        requests_content = "\n\n".join(
            request.to_http_file(
                base_url="{{BASE_URL}}",
                include_examples=include_examples,
                include_schema=include_schema,
            )
            for request in self.requests
        )
        parts.append(requests_content)

        return "\n\n".join(parts)

    def _get_editor_header(self, editor_mode: EditorMode) -> str:
        """Generate editor-specific header comments."""
        if editor_mode == EditorMode.DEFAULT:
            return ""
        elif editor_mode == EditorMode.KULALA:
            return (
                "# Kulala.nvim HTTP file\n"
                "# https://github.com/mistweaverco/kulala.nvim\n"
                "# Supports: {{variable}}, # @name, pre/post scripts"
            )
        elif editor_mode == EditorMode.PYCHARM:
            return (
                "# JetBrains HTTP Client file\n"
                "# Supports: {{variable}}, # @name, > {% %} response handlers\n"
                "# Docs: https://www.jetbrains.com/help/idea/http-client-in-product-code-editor.html"
            )
        elif editor_mode == EditorMode.HTTPYAC:
            return (
                "# httpyac HTTP file\n"
                "# https://httpyac.github.io/\n"
                "# Supports: {{variable}}, {{$dynamic}}, # @name, IntelliJ syntax"
            )
        return ""
