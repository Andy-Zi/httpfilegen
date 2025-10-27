from pydantic import BaseModel, Field
from typing import Dict, Optional
import json

class HttpRequest(BaseModel):
    method: str = Field(..., description="HTTP method, e.g., GET, POST")
    url: str = Field(..., description="Request URL")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Headers as key-value pairs")
    body: Optional[Dict] = Field(None, description="Request body as JSON dict")

    def to_http_file(self) -> str:
        lines = [f"{self.method} {self.url}"]
        if self.headers:
            lines.extend(f"{k}: {v}" for k, v in self.headers.items())
        lines.append("")  # Empty line before body
        if self.body:
            lines.append(json.dumps(self.body, indent=2))
        return "\n".join(lines)
