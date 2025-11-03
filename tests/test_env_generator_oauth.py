import json
from typer.testing import CliRunner


def test_env_oauth2_public_private(cli_app, tmp_path):
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
    res = runner.invoke(cli_app, ["generate", str(spec), "--out", str(out_file), "--overwrite"])
    assert res.exit_code == 0, res.output

    public_env = out_file.parent / "http-client.env.json"
    private_env = out_file.parent / "http-client.private.env.json"

    pub = json.loads(public_env.read_text())
    prv = json.loads(private_env.read_text())
    assert "dev" in pub
    assert "dev" in prv

    # Public may or may not include Security/Auth depending on what can be derived from flows
    sec = pub["dev"].get("Security")
    if sec is not None:
        assert isinstance(sec, dict)
        auth = sec.get("Auth")
        assert auth is None or isinstance(auth, dict)

    # Private can include secrets skeleton
    prv_sec = prv["dev"].get("Security")
    if prv_sec:
        assert isinstance(prv_sec, dict)
        pauth = prv_sec.get("Auth")
        if pauth:
            assert isinstance(pauth, dict)
