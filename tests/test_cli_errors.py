from typer.testing import CliRunner
from pathlib import Path


def test_generate_overwrite_refusal(cli_app, sample_spec_path, tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "file.http"

    # First generate
    res1 = runner.invoke(
        cli_app, ["generate", str(sample_spec_path), "--out", str(out)]
    )
    assert res1.exit_code == 0, res1.output

    # Second without overwrite should fail
    res2 = runner.invoke(
        cli_app, ["generate", str(sample_spec_path), "--out", str(out)]
    )
    assert res2.exit_code != 0
    assert "Refusing to overwrite" in res2.output


def test_env_overwrite_refusal(cli_app, sample_spec_path, tmp_path: Path) -> None:
    runner = CliRunner()

    # First env generation
    res1 = runner.invoke(
        cli_app,
        [
            "env",
            str(sample_spec_path),
            "--out-dir",
            str(tmp_path),
        ],
    )
    assert res1.exit_code == 0, res1.output

    # Second env generation without overwrite should fail
    res2 = runner.invoke(
        cli_app,
        [
            "env",
            str(sample_spec_path),
            "--out-dir",
            str(tmp_path),
        ],
    )
    assert res2.exit_code != 0
    assert "Refusing to overwrite existing file without --overwrite" in res2.output


def test_paths_method_filter(cli_app, sample_spec_path) -> None:
    runner = CliRunner()
    res = runner.invoke(
        cli_app, ["paths", str(sample_spec_path), "-m", "get", "-m", "post"]
    )
    assert res.exit_code == 0, res.output
    assert "/items" in res.output


def test_info_json(cli_app, sample_spec_path) -> None:
    runner = CliRunner()
    res = runner.invoke(cli_app, ["info", str(sample_spec_path), "--json"])
    assert res.exit_code == 0
    assert '"servers"' in res.output
