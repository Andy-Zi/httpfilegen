from typer.testing import CliRunner


def test_info_and_paths(cli_app, sample_spec_path):
    runner = CliRunner()

    # info as table
    res_info = runner.invoke(cli_app, ["info", str(sample_spec_path)])
    assert res_info.exit_code == 0, res_info.output
    assert "Servers:" in res_info.output

    # info as json
    res_info_json = runner.invoke(cli_app, ["info", str(sample_spec_path), "--json"])
    assert res_info_json.exit_code == 0, res_info_json.output
    assert "\"servers\"" in res_info_json.output

    # paths
    res_paths = runner.invoke(cli_app, ["paths", str(sample_spec_path)])
    assert res_paths.exit_code == 0, res_paths.output
    assert "/items" in res_paths.output

    # paths with method filter
    res_paths_get = runner.invoke(cli_app, ["paths", str(sample_spec_path), "-m", "get"]) 
    assert res_paths_get.exit_code == 0, res_paths_get.output
    assert "/items" in res_paths_get.output
