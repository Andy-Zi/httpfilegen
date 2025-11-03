from pathlib import Path
from http_file_generator import HtttpFileGenerator
from http_file_generator.models import HttpSettings


def test_base_url_only_first_active(tmp_path: Path):
    # Spec with two servers; add a settings baseURL as well.
    # Sorted order by URL will be: aaa < mmm < zzz
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        """
openapi: 3.0.3
info:
  title: X
  version: '1.0'
servers:
  - url: https://zzz.example.com
  - url: https://aaa.example.com
paths:
  /p:
    get:
      responses:
        '200':
          description: ok
""".strip()
    )

    out = tmp_path / "out.http"
    gen = HtttpFileGenerator(spec, settings=HttpSettings(baseURL="https://mmm.example.com"))
    gen.to_http_file(out)

    content = out.read_text()
    # Collect lines in the Shared section with BASE_URL assignments
    base_lines = [ln for ln in content.splitlines() if "BASE_URL=" in ln]
    # Exactly one active assignment (no leading '#')
    active = [ln for ln in base_lines if not ln.strip().startswith("#")]
    commented = [ln for ln in base_lines if ln.strip().startswith("#")]
    assert len(active) == 1
    assert len(commented) >= 1
    # The active one should be the smallest URL lexicographically: https://aaa.example.com
    assert active[0].strip() == "@BASE_URL=https://aaa.example.com" 
    # The settings-provided URL should be present but commented
    assert any("# @BASE_URL=https://mmm.example.com" in ln for ln in commented)
