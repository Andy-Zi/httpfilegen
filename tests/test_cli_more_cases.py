from typer.testing import CliRunner
from pathlib import Path
import json


def test_generate_no_env(cli_app, sample_spec_path, tmp_path: Path):
    runner = CliRunner()
    out_file = tmp_path / "o.http"
    res = runner.invoke(cli_app, ["generate", str(sample_spec_path), "--out", str(out_file), "--no-env"])
    assert res.exit_code == 0, res.output
    # env files should not exist
    assert not (tmp_path / "http-client.env.json").exists()
    assert not (tmp_path / "http-client.private.env.json").exists()


esspec_no_servers = """
openapi: 3.0.3
info:
  title: N
  version: '1.0'
paths:
  /x:
    get:
      responses:
        '200':
          description: ok
"""

def test_info_no_servers_or_security(cli_app, tmp_path: Path):
    spec = tmp_path / "n.yaml"
    spec.write_text(esspec_no_servers)
    runner = CliRunner()
    res = runner.invoke(cli_app, ["info", str(spec)])
    assert res.exit_code == 0, res.output
    # Should show zero paths or servers
    res_json = runner.invoke(cli_app, ["info", str(spec), "--json"])
    data = json.loads(res_json.output)
    assert data.get("servers") == [] or isinstance(data.get("servers"), list)


def test_paths_no_methods_flag(cli_app, sample_spec_path):
    runner = CliRunner()
    res = runner.invoke(cli_app, ["paths", str(sample_spec_path), "--no-with-methods"])
    assert res.exit_code == 0
    # Output should just be the path line
    assert "/items" in res.output


spec_with_examples = """
openapi: 3.0.3
info:
  title: E
  version: '1.0'
servers:
  - url: https://api.example.com
paths:
  /e:
    post:
      requestBody:
        content:
          application/json:
            examples:
              ex1:
                value:
                  hello: world
      responses:
        '200':
          description: ok
          content:
            application/json:
              examples:
                ex:
                  value:
                    ok: true
"""

def test_sample_with_examples(cli_app, tmp_path: Path):
    spec = tmp_path / "e.yaml"
    spec.write_text(spec_with_examples)

    runner = CliRunner()
    res = runner.invoke(cli_app, [
        "sample",
        str(spec),
        "/e",
        "--method",
        "post",
    ])
    assert res.exit_code == 0, res.output
    out = json.loads(res.output)
    assert out["request"]["POST"]["application/json"]["hello"] == "world"
    assert out["response"]["POST"]["200"]["application/json"]["ok"] is True
