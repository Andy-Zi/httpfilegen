from openapi_pydantic import PathItem
from pydantic import BaseModel, Field

from .request import HttpRequest


class HttpFileData(BaseModel):
    base_urls: set[str] = Field(..., description="Base URL for all requests")
    # auth: str | None = Field(None, description="Authorization header value")
    requests: list[HttpRequest] = Field(..., description="List of HTTP requests")

    @classmethod
    def from_paths(cls, base_urls: set[str], paths: dict[str, PathItem]):
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
        return cls(
            base_urls=base_urls,
            requests=requests,
        )

    def to_http_file(self):
        """
        Convert the data to an HTTP file string
        """
        http_file = ""
        # env vars
        http_file += "### System wide env vars\n\n"
        ## base url
        base_lines = []
        for base_url in self.base_urls:
            if base_lines:
                base_lines.append(f"# @BASE_URL = {base_url}")
            else:
                base_lines.append(f"@BASE_URL = {base_url}")
        http_file += "\n".join(base_lines) + "\n\n\n"

        # requests
        http_file += "\n\n".join(
            request.to_http_file(base_url="{{BASE_URL}}") for request in self.requests
        )
        return http_file
