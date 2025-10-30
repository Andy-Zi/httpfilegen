from pydantic import BaseModel, Field


class HttpScript(BaseModel):
    script: str = Field(..., description="The script to execute")
