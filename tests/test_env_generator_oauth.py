import json
from typer.testing import CliRunner


def test_env_oauth2_public_private(cli_app, tmp_path) -> None:
    # Spec with oauth2 client credentials
    spec_text = """
openapi: 3.0.3
info:
  title: E
  version: '1.0'
servers:
  - url: https://example.com
components:
  securitySchemes:
    auth0:
      type: oauth2
      flows:
        clientCredentials:
          tokenUrl: https://id.example.com/oauth/token
          scopes:
            read: Read access
paths:
  /ping:
    get:
      security:
        - auth0: []
      responses:
        '200':
          description: ok
    """
    spec = tmp_path / "e.yaml"
    spec.write_text(spec_text)

    runner = CliRunner()
    out_file = tmp_path / "ping.http"
    res = runner.invoke(
        cli_app, ["generate", str(spec), "--out", str(out_file), "--overwrite"]
    )
    assert res.exit_code == 0, res.output

    public_env = out_file.parent / "http-client.env.json"
    private_env = out_file.parent / "http-client.private.env.json"

    pub = json.loads(public_env.read_text())
    prv = json.loads(private_env.read_text())
    assert "dev" in pub
    assert "dev" in prv

    pub_auth = pub["dev"]["Security"]["Auth"]["auth0"]
    assert pub_auth["Grant Type"] == "Client Credentials"
    assert pub_auth["Token URL"] == "https://id.example.com/oauth/token"
    assert pub_auth["Client ID"] == "CHANGE_ME"
    assert pub_auth["Scope"] == "read"
    assert "Client Secret" not in pub_auth

    prv_auth = prv["dev"]["Security"]["Auth"]["auth0"]
    assert prv_auth["Client Secret"] == "CHANGE_ME"
