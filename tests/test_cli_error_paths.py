from typer.testing import CliRunner
from pathlib import Path


def test_generate_invalid_spec_path(cli_app, tmp_path: Path):
    runner = CliRunner()
    bad = tmp_path / "missing.yaml"
    res = runner.invoke(cli_app, ["generate", str(bad)])
    assert res.exit_code != 0
    assert "Spec file not found" in res.output


def test_paths_invalid_method_flag(cli_app, sample_spec_path):
    runner = CliRunner()
    res = runner.invoke(cli_app, ["paths", str(sample_spec_path), "-m", "invalid"]) 
    assert res.exit_code != 0
    assert "Unknown method" in res.output


def test_sample_invalid_method_flag(cli_app, sample_spec_path):
    runner = CliRunner()
    res = runner.invoke(cli_app, ["sample", str(sample_spec_path), "/items", "-m", "invalid"])
    assert res.exit_code != 0
    assert "Unknown method" in res.output


def test_env_overwrite_happy_path(cli_app, sample_spec_path, tmp_path: Path):
    runner = CliRunner()
    # First generate env files
    res1 = runner.invoke(cli_app, [
        "env",
        str(sample_spec_path),
        "--out-dir",
        str(tmp_path),
    ])
    assert res1.exit_code == 0
    # Second with overwrite should succeed
    res2 = runner.invoke(cli_app, [
        "env",
        str(sample_spec_path),
        "--out-dir",
        str(tmp_path),
        "--overwrite",
    ])
    assert res2.exit_code == 0, res2.output
