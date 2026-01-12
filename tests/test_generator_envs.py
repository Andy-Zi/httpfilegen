from pathlib import Path
import json


def test_generate_env_files_from_model(sample_spec_path, tmp_path: Path) -> None:
    from http_file_generator import HtttpFileGenerator

    gen = HtttpFileGenerator(sample_spec_path)

    public_env = tmp_path / "http-client.env.json"
    private_env = tmp_path / "http-client.private.env.json"
    gen.to_env_files(public_env, private_env, env_name="dev")

    # Files should exist
    assert public_env.exists()
    assert private_env.exists()

    # Validate structure has 'dev' with expected sections
    pub = json.loads(public_env.read_text())
    prv = json.loads(private_env.read_text())

    assert "dev" in pub
    assert "dev" in prv

    # Public env may include Security/Auth for oauth2
    # Private env may include secrets/variables
    # Ensure JSON is valid and sections present
    assert isinstance(pub["dev"], dict)
    assert isinstance(prv["dev"], dict)


def test_generate_env_files_multiple_servers(tmp_path: Path) -> None:
    """Test environment generation with multiple servers."""
    from http_file_generator import HtttpFileGenerator
    from http_file_generator.models import HttpSettings

    # Create spec with multiple servers
    spec_content = {
        "openapi": "3.0.3",
        "info": {"title": "Multi Server Test", "version": "1.0"},
        "servers": [
            {"url": "https://api1.example.com"},
            {"url": "https://api2.example.com"},
        ],
        "paths": {"/test": {"get": {"responses": {"200": {"description": "OK"}}}}},
    }

    spec_file = tmp_path / "multi_server.json"
    import json

    spec_file.write_text(json.dumps(spec_content))

    gen = HtttpFileGenerator(spec_file)

    public_env = tmp_path / "public.json"
    private_env = tmp_path / "private.json"
    gen.to_env_files(public_env, private_env, env_name="dev")

    pub = json.loads(public_env.read_text())
    prv = json.loads(private_env.read_text())

    # Should have dev, dev2 environments for the two servers
    assert "dev" in pub
    assert "dev2" in pub
    assert "dev" in prv
    assert "dev2" in prv

    # Check BASE_URL values
    assert pub["dev"]["BASE_URL"] == "https://api1.example.com"
    assert pub["dev2"]["BASE_URL"] == "https://api2.example.com"


def test_generate_env_files_custom_base_url(tmp_path: Path) -> None:
    """Test environment generation with custom base URL."""
    from http_file_generator import HtttpFileGenerator
    from http_file_generator.models import HttpSettings

    spec_content = {
        "openapi": "3.0.3",
        "info": {"title": "Custom Base URL Test", "version": "1.0"},
        "servers": [{"url": "https://api.example.com"}],
        "paths": {"/test": {"get": {"responses": {"200": {"description": "OK"}}}}},
    }

    spec_file = tmp_path / "custom_base.json"
    import json

    spec_file.write_text(json.dumps(spec_content))

    # Create generator with custom base URL
    from pydantic_core import Url

    gen = HtttpFileGenerator(
        spec_file, HttpSettings(baseURL=Url("https://custom.example.com"))
    )

    public_env = tmp_path / "public.json"
    private_env = tmp_path / "private.json"
    gen.to_env_files(public_env, private_env, env_name="dev")

    pub = json.loads(public_env.read_text())

    # Should have dev (from server) and dev2 (from custom base URL)
    assert "dev" in pub
    assert "dev2" in pub
    assert pub["dev"]["BASE_URL"] == "https://api.example.com"
    assert (
        pub["dev2"]["BASE_URL"] == "https://custom.example.com/"
    )  # Note trailing slash


def test_generate_env_files_no_servers(tmp_path: Path) -> None:
    """Test environment generation when spec has no servers."""
    from http_file_generator import HtttpFileGenerator

    spec_content = {
        "openapi": "3.0.3",
        "info": {"title": "No Servers Test", "version": "1.0"},
        "paths": {"/test": {"get": {"responses": {"200": {"description": "OK"}}}}},
    }

    spec_file = tmp_path / "no_servers.json"
    import json

    spec_file.write_text(json.dumps(spec_content))

    gen = HtttpFileGenerator(spec_file)

    public_env = tmp_path / "public.json"
    private_env = tmp_path / "private.json"
    gen.to_env_files(public_env, private_env, env_name="dev")

    pub = json.loads(public_env.read_text())
    prv = json.loads(private_env.read_text())

    # Should have default environment with placeholder BASE_URL
    assert "dev" in pub
    assert "dev" in prv
    assert "BASE_URL" in pub["dev"]
    assert pub["dev"]["BASE_URL"] == "/"  # OpenAPI default server URL
