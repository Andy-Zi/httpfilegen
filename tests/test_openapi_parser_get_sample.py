from http_file_generator.models.http_file.open_api_parser import OpenApiParser


def test_get_sample_for_path_with_examples_and_none(tmp_path) -> None:
    spec = tmp_path / "samp.yaml"
    spec.write_text(
        """
openapi: 3.0.3
info:
  title: S
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
                  kk: vv
      responses:
        '200':
          description: ok
  /empty:
    get:
      responses:
        '204':
          description: no content
        
        """
    )
    p = OpenApiParser(spec)
    samples = p.get_sample_for_path("/e")
    assert "POST" in samples and isinstance(samples["POST"], dict)
    assert samples["POST"]["kk"] == "vv"

    samples2 = p.get_sample_for_path("/empty")
    assert "GET" in samples2 and samples2["GET"] is None
