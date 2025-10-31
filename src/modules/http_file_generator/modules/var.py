from pydantic import BaseModel, Field


class HttpVariable(BaseModel):
    name: str = Field(..., description="Name of the variable")
    value: str = Field(..., description="Value of the variable")
    description: str = Field("", description="Description of the variable")

    def __str__(self) -> str:
        return f"{'# ' + self.description + '\n' if self.description else ''}@{self.name}={self.value}\n"

    def __hash__(self) -> int:
        return hash((self.name, self.value))

class BaseURL(HttpVariable):
    name: str = Field("BASE_URL", description="Name of the variable")
