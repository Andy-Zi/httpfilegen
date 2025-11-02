from pydantic import BaseModel, Field


class HttpVariable(BaseModel):
    name: str = Field(..., description="Name of the variable")
    value: str = Field(..., description="Value of the variable")
    description: str = Field("", description="Description of the variable")

    def __str__(self) -> str:
        lines = ""
        if self.description:
            if "\n" in self.description:
                desc = "\n".join(
                    [f"# {line}".rstrip() for line in self.description.splitlines()]
                )
            else:
                desc = f"# {self.description}"
            lines += f"{desc + '\n' or ''}"
        if self.value:
            lines += f"@{self.name}={self.value}\n"
            return lines
            # return f"{'# ' + self.description + '\n' if self.description else ''}@{self.name}={self.value}\n"
        lines += f"# @prompt{self.name}\n"
        return lines
        # return f"{'# ' + self.description + '\n' if self.description else ''}# @prompt {self.name}\n"

    def __hash__(self) -> int:
        return hash((self.name, self.value))

class BaseURL(HttpVariable):
    name: str = Field("BASE_URL", description="Name of the variable")
