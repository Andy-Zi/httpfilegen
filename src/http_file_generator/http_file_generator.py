from pathlib import Path

from .models import HttpFileData, HttpClientBaseEnv, OpenApiParser


class HtttpFileGenerator:
    env_files: dict[Path, HttpClientBaseEnv]

    def __init__(self, file: Path):
        parser = OpenApiParser(file)
        self.http_file = HttpFileData.from_paths(
            server=parser.model.servers,
            paths=parser.model.paths or {},
        )

    def to_http_file(self, out_path: Path):
        lines = self.http_file.to_http_file()
        with Path.open(out_path, "w") as f:
            f.writelines(lines)
