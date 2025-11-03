from typer.testing import CliRunner


def test_sample(cli_app, sample_spec_path):
    runner = CliRunner()

    res = runner.invoke(
        cli_app,
        [
            "sample",
            str(sample_spec_path),
            "/items",
            "--method",
            "get",
            "--content-type",
            "application/json",
        ],
    )
    assert res.exit_code == 0, res.output
    # Should output JSON
    assert res.output.strip().startswith("{")
    assert '"path": "/items"' in res.output
