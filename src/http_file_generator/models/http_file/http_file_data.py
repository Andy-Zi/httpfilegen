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
    ):
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
        for server in server:
            base_urls.add(
                BaseURL(value=server.url, description=server.description or "")
            )

        return cls(
            base_urls=base_urls,
            requests=requests,
        )

    def to_http_file(self, include_examples: bool = False, include_schema: bool = False):
        """
        Convert the data to an HTTP file string
        """
        http_file = ""
        base_lines = []
        # shared params
        http_file += "### Shared\n\n"
        # Deterministic order, then comment-out all but the first
        ordered_base_urls = sorted(list(self.base_urls), key=lambda b: b.value)
        if ordered_base_urls:
            # First stays active
            base_lines.append(str(ordered_base_urls[0]).rstrip("\n"))
            # Others are commented to avoid multiple active BASE_URL declarations
            for bu in ordered_base_urls[1:]:
                for ln in str(bu).splitlines():
                    if ln.strip():
                        base_lines.append(f"# {ln}")
                    else:
                        base_lines.append("")
        http_file += "\n".join(base_lines) + "\n\n\n"

        # requests
        http_file += "\n\n".join(
            request.to_http_file(
                base_url="{{BASE_URL}}",
                include_examples=include_examples,
                include_schema=include_schema,
            )
            for request in self.requests
        )
        return http_file
