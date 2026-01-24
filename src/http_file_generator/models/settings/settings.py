from enum import StrEnum, auto
from pydantic import Field
from pydantic_core import Url
from pydantic_settings import BaseSettings


class Filemode(StrEnum):
    SINGLE = auto()
    MULTI = auto()


class EditorMode(StrEnum):
    """Editor-specific output modes for .http file generation."""

    DEFAULT = auto()  # Cross-compatible (IntelliJ spec baseline)
    KULALA = auto()  # Kulala.nvim (Neovim)
    PYCHARM = auto()  # JetBrains IntelliJ/PyCharm
    HTTPYAC = auto()  # httpyac (VS Code)


class HttpSettings(BaseSettings):
    filemode: Filemode = Field(default=Filemode.SINGLE, frozen=True)
    baseURL: Url | None = Field(default=None, frozen=True)
    include_examples: bool = Field(default=False, frozen=True)
    include_schema: bool = Field(default=False, frozen=True)
    editor_mode: EditorMode = Field(default=EditorMode.DEFAULT, frozen=True)
