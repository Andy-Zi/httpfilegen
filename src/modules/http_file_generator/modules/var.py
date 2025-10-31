from pydantic import BaseModel, Field


class HttpVariable(BaseModel):
    name: str = Field(..., description="Name of the variable")
    value: str = Field(..., description="Value of the variable")
    description: str = Field("", description="Description of the variable")

    def __str__(self) -> str:
        return f"# {self.description}\n@{self.name}={self.value}\n"
