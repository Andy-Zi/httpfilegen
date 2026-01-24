"""Tests for --dry-run and validate CLI features."""

from pathlib import Path

from typer.testing import CliRunner


class TestDryRun:
    """Tests for --dry-run option."""

    def test_dry_run_does_not_write_files(
        self, cli_app, sample_spec_path, tmp_path: Path
    ) -> None:
        """Test that --dry-run previews output without writing files."""
        runner = CliRunner()
        out_file = tmp_path / "out.http"
        result = runner.invoke(
            cli_app,
            [
                "generate",
                str(sample_spec_path),
                "--out",
                str(out_file),
                "--dry-run",
            ],
        )
        assert result.exit_code == 0, result.output
        assert not out_file.exists(), "File should not be created in dry-run mode"

        # Env files should not be created either
        env_file = tmp_path / "http-client.env.json"
        private_env = tmp_path / "http-client.private.env.json"
        assert not env_file.exists()
        assert not private_env.exists()

    def test_dry_run_shows_preview(
        self, cli_app, sample_spec_path, tmp_path: Path
    ) -> None:
        """Test that --dry-run shows content preview."""
        runner = CliRunner()
        out_file = tmp_path / "out.http"
        result = runner.invoke(
            cli_app,
            [
                "generate",
                str(sample_spec_path),
                "--out",
                str(out_file),
                "--dry-run",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "DRY RUN MODE" in result.output
        assert "Would write to:" in result.output
        assert "HTTP File Content Preview" in result.output
        # Should show actual HTTP content
        assert "GET" in result.output or "POST" in result.output

    def test_dry_run_shows_env_info(
        self, cli_app, sample_spec_path, tmp_path: Path
    ) -> None:
        """Test that --dry-run shows env file info when enabled."""
        runner = CliRunner()
        out_file = tmp_path / "out.http"
        result = runner.invoke(
            cli_app,
            [
                "generate",
                str(sample_spec_path),
                "--out",
                str(out_file),
                "--dry-run",
                "--env",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Would also generate env files" in result.output
        assert "http-client.env.json" in result.output
        assert "http-client.private.env.json" in result.output

    def test_dry_run_no_env_message(
        self, cli_app, sample_spec_path, tmp_path: Path
    ) -> None:
        """Test that --dry-run with --no-env doesn't mention env files."""
        runner = CliRunner()
        out_file = tmp_path / "out.http"
        result = runner.invoke(
            cli_app,
            [
                "generate",
                str(sample_spec_path),
                "--out",
                str(out_file),
                "--dry-run",
                "--no-env",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Would also generate env files" not in result.output

    def test_dry_run_multi_mode(
        self, cli_app, sample_spec_path, tmp_path: Path
    ) -> None:
        """Test that --dry-run shows MULTI mode info."""
        runner = CliRunner()
        out_file = tmp_path / "out.http"
        result = runner.invoke(
            cli_app,
            [
                "generate",
                str(sample_spec_path),
                "--out",
                str(out_file),
                "--dry-run",
                "--filemode",
                "multi",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Mode: MULTI" in result.output


class TestValidate:
    """Tests for validate command."""

    def test_validate_valid_spec(self, cli_app, sample_spec_path) -> None:
        """Test validating a valid spec."""
        runner = CliRunner()
        result = runner.invoke(
            cli_app,
            ["validate", str(sample_spec_path)],
        )
        assert result.exit_code == 0, result.output
        assert "Validation OK" in result.output
        assert "OpenAPI version:" in result.output
        assert "Title:" in result.output

    def test_validate_valid_spec_json_output(self, cli_app, sample_spec_path) -> None:
        """Test validating with JSON output."""
        runner = CliRunner()
        result = runner.invoke(
            cli_app,
            ["validate", str(sample_spec_path), "--json"],
        )
        assert result.exit_code == 0, result.output
        assert '"valid": true' in result.output
        assert '"openapi_version":' in result.output
        assert '"paths_count":' in result.output

    def test_validate_invalid_spec(self, cli_app, tmp_path: Path) -> None:
        """Test validating an invalid spec."""
        invalid_spec = tmp_path / "invalid.yaml"
        invalid_spec.write_text("not: a valid openapi spec")

        runner = CliRunner()
        result = runner.invoke(
            cli_app,
            ["validate", str(invalid_spec)],
        )
        assert result.exit_code == 1
        assert "Validation FAILED" in result.output

    def test_validate_invalid_spec_json_output(self, cli_app, tmp_path: Path) -> None:
        """Test validating invalid spec with JSON output."""
        invalid_spec = tmp_path / "invalid.yaml"
        invalid_spec.write_text("not: a valid openapi spec")

        runner = CliRunner()
        result = runner.invoke(
            cli_app,
            ["validate", str(invalid_spec), "--json"],
        )
        assert result.exit_code == 1
        assert '"valid": false' in result.output
        assert '"errors":' in result.output

    def test_validate_nonexistent_file(self, cli_app, tmp_path: Path) -> None:
        """Test validating a nonexistent file."""
        runner = CliRunner()
        result = runner.invoke(
            cli_app,
            ["validate", str(tmp_path / "nonexistent.yaml")],
        )
        assert result.exit_code == 1
        assert "Spec file not found" in result.output

    def test_validate_malformed_yaml(self, cli_app, tmp_path: Path) -> None:
        """Test validating malformed YAML."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("{{{{ invalid yaml syntax")

        runner = CliRunner()
        result = runner.invoke(
            cli_app,
            ["validate", str(bad_yaml)],
        )
        assert result.exit_code == 1

    def test_validate_shows_spec_info(self, cli_app, sample_spec_path) -> None:
        """Test that validate shows spec metadata on success."""
        runner = CliRunner()
        result = runner.invoke(
            cli_app,
            ["validate", str(sample_spec_path)],
        )
        assert result.exit_code == 0, result.output
        assert "Sample API" in result.output  # Title from fixture
        assert "Paths:" in result.output
        assert "Servers:" in result.output
