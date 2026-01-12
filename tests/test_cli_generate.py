from pathlib import Path

from typer.testing import CliRunner


def test_generate_http_file(cli_app, sample_spec_path, tmp_path: Path) -> None:
    runner = CliRunner()
    out_file = tmp_path / "out.http"
    result = runner.invoke(
        cli_app,
        [
            "generate",
            str(sample_spec_path),
            "--out",
            str(out_file),
            "--env-name",
            "dev",
            "--overwrite",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_file.exists()

    # Check that the output contains expected content
    content = out_file.read_text()
    assert "###" in content  # Request separators
    assert "GET" in content or "POST" in content  # HTTP methods

    # Check that env files were created
    env_file = tmp_path / "http-client.env.json"
    private_env_file = tmp_path / "http-client.private.env.json"
    assert env_file.exists()
    assert private_env_file.exists()

    # Check env file content
    env_content = env_file.read_text()
    assert (
        '"dev":' in env_content
    )  # Environment section created, "HTTP file should be created"

    # Check env files are also created by default
    public_env = out_file.parent / "http-client.env.json"
    private_env = out_file.parent / "http-client.private.env.json"
    assert public_env.exists(), "Public env should be created"
    assert private_env.exists(), "Private env should be created"

    # Basic content sanity
    data = out_file.read_text()
    assert "GET" in data or "POST" in data
    # Check that BASE_URL is referenced in requests but not in a shared block
    assert "{{BASE_URL}}" in data


def test_generate_without_env_files(cli_app, sample_spec_path, tmp_path: Path) -> None:
    """Test generating HTTP files without environment files."""
    runner = CliRunner()
    out_file = tmp_path / "out.http"
    result = runner.invoke(
        cli_app,
        [
            "generate",
            str(sample_spec_path),
            "--out",
            str(out_file),
            "--no-env",
            "--overwrite",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_file.exists()

    # Check that env files were NOT created
    env_file = tmp_path / "http-client.env.json"
    private_env_file = tmp_path / "http-client.private.env.json"
    assert not env_file.exists()
    assert not private_env_file.exists()


def test_generate_custom_env_name(cli_app, sample_spec_path, tmp_path: Path) -> None:
    """Test generating with custom environment name."""
    runner = CliRunner()
    out_file = tmp_path / "out.http"
    result = runner.invoke(
        cli_app,
        [
            "generate",
            str(sample_spec_path),
            "--out",
            str(out_file),
            "--env-name",
            "staging",
            "--overwrite",
        ],
    )
    assert result.exit_code == 0, result.output

    # Check env file contains custom name
    env_file = tmp_path / "http-client.env.json"
    env_content = env_file.read_text()
    assert '"staging":' in env_content


def test_generate_custom_base_url(cli_app, sample_spec_path, tmp_path: Path) -> None:
    """Test generating with custom base URL."""
    runner = CliRunner()
    out_file = tmp_path / "out.http"
    result = runner.invoke(
        cli_app,
        [
            "generate",
            str(sample_spec_path),
            "--out",
            str(out_file),
            "--base-url",
            "https://custom-api.example.com",
            "--overwrite",
        ],
    )
    assert result.exit_code == 0, result.output

    # Check that custom base URL appears in env file
    env_file = tmp_path / "http-client.env.json"
    env_content = env_file.read_text()
    assert '"BASE_URL": "https://custom-api.example.com/"' in env_content


def test_generate_filemode_single(cli_app, sample_spec_path, tmp_path: Path) -> None:
    """Test generating with explicit single filemode."""
    runner = CliRunner()
    out_file = tmp_path / "out.http"
    result = runner.invoke(
        cli_app,
        [
            "generate",
            str(sample_spec_path),
            "--out",
            str(out_file),
            "--filemode",
            "single",
            "--overwrite",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_file.exists()
    assert out_file.is_file()  # Should be a single file


def test_generate_error_nonexistent_spec(cli_app, tmp_path: Path) -> None:
    """Test error handling for nonexistent spec file."""
    runner = CliRunner()
    out_file = tmp_path / "out.http"
    nonexistent_spec = tmp_path / "nonexistent.yaml"

    result = runner.invoke(
        cli_app,
        [
            "generate",
            str(nonexistent_spec),
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 1  # Should fail
    assert "Spec file not found" in result.output


def test_generate_error_overwrite_protection(
    cli_app, sample_spec_path, tmp_path: Path
) -> None:
    """Test overwrite protection for existing files."""
    runner = CliRunner()
    out_file = tmp_path / "out.http"

    # Create file first
    out_file.write_text("existing content")

    # Try to generate without overwrite
    result = runner.invoke(
        cli_app,
        [
            "generate",
            str(sample_spec_path),
            "--out",
            str(out_file),
        ],
    )
    assert result.exit_code == 1  # Should fail
    assert "Refusing to overwrite" in result.output
    assert out_file.read_text() == "existing content"  # File unchanged


def test_generate_error_invalid_filemode(
    cli_app, sample_spec_path, tmp_path: Path
) -> None:
    """Test error handling for invalid filemode."""
    runner = CliRunner()
    out_file = tmp_path / "out.http"

    result = runner.invoke(
        cli_app,
        [
            "generate",
            str(sample_spec_path),
            "--out",
            str(out_file),
            "--filemode",
            "invalid",
        ],
    )
    assert result.exit_code == 1  # Should fail
    assert (
        "Invalid value for" in result.output
        or "invalid choice" in result.output.lower()
    )
