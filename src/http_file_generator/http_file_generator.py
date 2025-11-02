from pathlib import Path

from .models import HttpFileData, HttpClientBaseEnv, OpenApiParser
from .models.env_file.generator import generate_env_dicts
import json


class HtttpFileGenerator:
    env_files: dict[Path, HttpClientBaseEnv]

    def __init__(self, file: Path):
        parser = OpenApiParser(file)
        components = parser.model.components
        security_schemes = components.securitySchemes if components else None
        self.http_file = HttpFileData.from_paths(
            server=parser.model.servers,
            paths=parser.model.paths or {},
            root_security=parser.model.security,
            security_schemes=security_schemes,  # type: ignore[arg-type]
        )
        self._openapi_model = parser.model

    def to_http_file(self, out_path: Path):
        lines = self.http_file.to_http_file()
        with Path.open(out_path, "w") as f:
            f.writelines(lines)

    def to_env_files(self, public_out: Path, private_out: Path, env_name: str = "dev"):
        """
        Generate http-client.env.json and http-client.private.env.json skeletons
        based on the OpenAPI security schemes.
        """
        public_env, private_env = generate_env_dicts(self._openapi_model, env_name=env_name)
        with Path.open(public_out, "w") as f:
            json.dump(public_env, f, indent=2)
        with Path.open(private_out, "w") as f:
            json.dump(private_env, f, indent=2)
