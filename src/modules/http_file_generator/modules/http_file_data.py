from typing import Union
from openapi_pydantic import PathItem
from openapi_pydantic.v3.v3_0 import Server as Server3_0
from openapi_pydantic.v3.v3_1 import Server as Server3_1
from pydantic import BaseModel, Field

from .request import HttpRequest
from .var import BaseURL

Server = Union[Server3_0, Server3_1]


class HttpFileData(BaseModel):
    base_urls: set[BaseURL] = Field(..., description="Base URL for all requests")
    # auth: str | None = Field(None, description="Authorization header value")
    requests: list[HttpRequest] = Field(..., description="List of HTTP requests")

    @classmethod
    def from_paths(cls, server: list[Server], paths: dict[str, PathItem]):
        """
        Convert a paths object to a list of HTTP requests
        """
        requests = []
        for path, path_item in paths.items():
            for method in path_item.model_dump(exclude_none=True):
                if method in [
                    "get",
                    "post",
                    "put",
                    "patch",
                    "delete",
                    "head",
                    "options",
                    "trace",
                ]:
                    operation = getattr(path_item, method)
                    if operation:
                        request = HttpRequest.from_operation(
                            path=path,
                            method=method.upper(),
                            operation=operation,
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

    def to_http_file(self):
        """
        Convert the data to an HTTP file string
        """
        http_file = ""
        base_lines = []
        # params
        for base_url in self.base_urls:
            base_lines.append(str(base_url))
        http_file += "\n".join(base_lines) + "\n\n\n"

        # requests
        http_file += "\n\n".join(
            request.to_http_file(base_url="{{BASE_URL}}") for request in self.requests
        )
        return http_file
