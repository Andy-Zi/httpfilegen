from pathlib import Path

from typer.testing import CliRunner


def test_batch_generates_multiple(cli_app, tmp_path: Path) -> None:
    # Build two simple specs
    spec1 = tmp_path / "a.yaml"
    spec1.write_text(
        """
openapi: 3.0.3
info:
  title: A
  version: '1.0'
servers:
  - url: https://api.example.com
paths:
  /a:
    get:
      responses:
        '200':
          description: ok

        """.strip()
    )

    spec2 = tmp_path / "b.yaml"
    spec2.write_text(
        """
openapi: 3.0.3
info:
  title: B
  version: '1.0'
servers:
  - url: https://api.example.com
paths:
  /b:
    post:
      responses:
        '201':
          description: created

        """.strip()
    )

    runner = CliRunner()
    res = runner.invoke(
        cli_app,
        [
            "batch",
            str(tmp_path),
            "--pattern",
            "*.yaml",
            "--env-name",
            "dev",
            "--overwrite",
        ],
    )
    assert res.exit_code == 0, res.output

    # Output files should exist for both
    out1 = tmp_path / "a.http"
    out2 = tmp_path / "b.http"
    assert out1.exists() and out2.exists()

    # Env files should exist (created at spec folder level once)
    pub = tmp_path / "http-client.env.json"
    prv = tmp_path / "http-client.private.env.json"
    assert pub.exists() and prv.exists()
