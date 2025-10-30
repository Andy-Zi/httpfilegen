from enum import StrEnum, auto
from typing import Literal
from pydantic import Field
from pydantic_core import Url
from pydantic_settings import BaseSettings, SettingsConfigDict

class Filemode(StrEnum):
    SINGLE = auto()
    MULTI = auto()


class HttpSettings(BaseSettings):
    filemode: Filemode = Field(default=Filemode.SINGLE, frozen=True)
    baseURL: Url | None = Field(default=None, frozen=True)
    include_examples: bool = Field(default=False, frozen=True)
    include_schema: bool = Field(default=False, frozen=True)
