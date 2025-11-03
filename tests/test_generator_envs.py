from pathlib import Path
import json


def test_generate_env_files_from_model(sample_spec_path, tmp_path: Path):
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
