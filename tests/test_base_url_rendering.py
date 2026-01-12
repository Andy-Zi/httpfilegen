from pathlib import Path
from typing import cast
from pydantic_core import Url
from http_file_generator import HtttpFileGenerator
from http_file_generator.models import HttpSettings


def test_multiple_servers_create_multiple_environments(tmp_path: Path) -> None:
    # Spec with two servers; add a settings baseURL as well.
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        """
openapi: 3.0.3
info:
  title: X
  version: '1.0'
servers:
  - url: https://aaa.example.com
  - url: https://zzz.example.com
paths:
  /p:
    get:
      responses:
        '200':
          description: ok
""".strip()
    )

    out = tmp_path / "out.http"
    public_env = tmp_path / "http-client.env.json"
    private_env = tmp_path / "http-client.private.env.json"

    gen = HtttpFileGenerator(
        spec, settings=HttpSettings(baseURL=cast(Url, "https://mmm.example.com"))
    )
    gen.to_http_file(out)
    gen.to_env_files(public_env, private_env, env_name="dev")

    # Check HTTP file doesn't have shared block
    content = out.read_text()
    assert "### Shared" not in content
    assert "{{BASE_URL}}" in content

    # Check env files have multiple environments with BASE_URL
    env_content = public_env.read_text()
    assert '"dev":' in env_content  # First server
    assert '"dev2":' in env_content  # Second server
    assert '"dev3":' in env_content  # Custom base URL

    # Check BASE_URL values
    assert '"BASE_URL": "https://aaa.example.com"' in env_content
    assert '"BASE_URL": "https://zzz.example.com"' in env_content
    assert '"BASE_URL": "https://mmm.example.com"' in env_content
