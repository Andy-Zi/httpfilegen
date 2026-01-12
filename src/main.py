from pathlib import Path
from typing import cast
from pydantic_core import Url

from http_file_generator import HtttpFileGenerator
from http_file_generator.models import Filemode, HttpSettings

if __name__ == "__main__":
    spec = Path("../samples/httpbin/httpbin.json")
    # Example settings: filemode can be SINGLE (default) or MULTI.
    # baseURL is optional; when provided, it creates an additional environment.
    settings = HttpSettings(
        filemode=Filemode.SINGLE,
        baseURL=cast(
            Url, "https://httpbin.org"
        ),  # This will create an additional "dev2" environment
        include_examples=True,
        include_schema=True,
    )

    gen = HtttpFileGenerator(spec, settings=settings)

    # Generate HTTP file (no more shared block!)
    output_file = Path("openapi.http")
    gen.to_http_file(output_file)
    print(f"HTTP file generated: {output_file}")

    # Generate env files with BASE_URL in environments instead of shared block
    public_env_file = output_file.parent / "http-client.env.json"
    private_env_file = output_file.parent / "http-client.private.env.json"
    gen.to_env_files(public_env_file, private_env_file, env_name="dev")
    print(f"Env files generated: {public_env_file}, {private_env_file}")
