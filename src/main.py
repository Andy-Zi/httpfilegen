from pathlib import Path
from http_file_generator import HtttpFileGenerator
from http_file_generator.models import HttpSettings, Filemode

if __name__ == "__main__":
    spec = Path("../samples/httpbin/httpbin.json")
    # Example settings: filemode can be SINGLE (default) or MULTI.
    # baseURL is optional; when provided, it's added to the generated files.
    settings = HttpSettings(
        filemode=Filemode.MULTI,
        baseURL="https://api.example.com",
    )
    gen = HtttpFileGenerator(spec, settings=settings)

    # Will create ./openapi/<path>/index.http if you pass a .http path
    gen.to_http_file(Path("openapi.http"))

    # Or choose a target directory directly
    gen.to_http_file(Path("out-http"))
    #
    # output_file = f"{file.parent}/{file.stem}.http"
    # http_file_generator = HtttpFileGenerator(file)
    # http_file_generator.to_http_file(Path(output_file))
    # print(f"HTTP file generated: {output_file}")
    #
    # # Also generate env files next to the output http file
    # public_env_file = Path(file.parent) / "http-client.env.json"
    # private_env_file = Path(file.parent) / "http-client.private.env.json"
    # http_file_generator.to_env_files(public_env_file, private_env_file, env_name="dev")
    # print(f"Env files generated: {public_env_file}, {private_env_file}")
    #
    #
    #
    #
