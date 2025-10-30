from pathlib import Path

from .modules import HttpFileData, HttpClientBaseEnv
from modules.openapi_parser.open_api_parser import OpenApiParser


class HtttpFileGenerator:
    env_files: dict[Path, HttpClientBaseEnv]

    def __init__(self, openapi_parser: OpenApiParser):
        self.http_file = HttpFileData.from_paths(
            base_urls={server.url for server in openapi_parser.model.servers},
            paths=openapi_parser.model.paths or {},
        )

    def to_http_file(self, out_path: Path):
        lines = self.http_file.to_http_file()
        with Path.open(out_path, "w") as f:
            f.writelines(lines)
