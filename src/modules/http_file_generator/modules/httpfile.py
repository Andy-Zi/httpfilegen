from pydantic import BaseModel, Field

from .request import HttpRequest


class HttpFile(BaseModel):
    base_url: str = Field(..., description="Base URL for all requests")
    requests: list[HttpRequest] = Field(..., description="List of HTTP requests")
