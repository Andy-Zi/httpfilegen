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
    assert out_file.exists(), "HTTP file should be created"

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
