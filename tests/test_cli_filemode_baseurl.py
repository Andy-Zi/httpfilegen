from pathlib import Path
from typer.testing import CliRunner


def test_generate_multi_mode_creates_tree_and_env(cli_app, sample_spec_path, tmp_path: Path):
    runner = CliRunner()
    out = tmp_path / "out.http"
    res = runner.invoke(
        cli_app,
        [
            "generate",
            str(sample_spec_path),
            "--out",
            str(out),
            "--filemode",
            "MULTI",
        ],
    )
    assert res.exit_code == 0, res.output

    # In MULTI mode, outputs go under a directory derived from the out filename (stem)
    tree_dir = tmp_path / "out"
    # Path from sample_spec_path is /items -> items/index.http
    path_file = tree_dir / "items" / "index.http"
    assert path_file.exists(), f"Expected path file to exist: {path_file}"

    # Env files should be placed next to the generated tree by default
    public_env = tree_dir / "http-client.env.json"
    private_env = tree_dir / "http-client.private.env.json"
    assert public_env.exists()
    assert private_env.exists()

    content = path_file.read_text()
    assert "### Shared" in content
    # Should contain at least one operation from the sample
    assert "GET" in content or "POST" in content


def test_generate_single_mode_with_base_url(cli_app, sample_spec_path, tmp_path: Path):
    runner = CliRunner()
    out = tmp_path / "single.http"
    res = runner.invoke(
        cli_app,
        [
            "generate",
            str(sample_spec_path),
            "--out",
            str(out),
            "--base-url",
            "https://custom.example.com",
            "--overwrite",
        ],
    )
    assert res.exit_code == 0, res.output
    assert out.exists()
    data = out.read_text()
    # The explicit base URL should be included in the Shared section
    assert "@BASE_URL=https://custom.example.com" in data


def test_batch_multi_mode(cli_app, tmp_path: Path):
    # Build two tiny specs
    a = tmp_path / "a.yaml"
    a.write_text(
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

    b = tmp_path / "b.yaml"
    b.write_text(
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
            "--filemode",
            "MULTI",
            "--overwrite",
        ],
    )
    assert res.exit_code == 0, res.output

    # Expect directories next to specs, each with <path>/index.http
    a_tree = tmp_path / "a"
    b_tree = tmp_path / "b"
    assert (a_tree / "a" / "index.http").exists()
    assert (b_tree / "b" / "index.http").exists()

    # Env files should be in the tree roots
    assert (a_tree / "http-client.env.json").exists()
    assert (a_tree / "http-client.private.env.json").exists()
    assert (b_tree / "http-client.env.json").exists()
    assert (b_tree / "http-client.private.env.json").exists()
