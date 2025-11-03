import sys
from pathlib import Path
import textwrap
import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True, scope="session")
def add_src_to_path(project_root):
    src = project_root / "src"
    sys.path.insert(0, str(src))
    yield
    # best effort cleanup
    if str(src) in sys.path:
        sys.path.remove(str(src))


@pytest.fixture()
def sample_spec_path(tmp_path: Path) -> Path:
    """Create a minimal OpenAPI 3.0 spec with GET/POST and some security schemes."""
    content = textwrap.dedent(
        """
        openapi: 3.0.3
        info:
          title: Sample API
          version: '1.0'
        servers:
          - url: https://api.example.com
        paths:
          /items:
            get:
              summary: List items
              description: Returns items
              responses:
                '200':
                  description: OK
                  content:
                    application/json:
                      schema:
                        type: object
                        properties:
                          items:
                            type: array
                            items:
                              type: string
            post:
              summary: Create item
              requestBody:
                required: false
                content:
                  application/json:
                    schema:
                      type: object
                      properties:
                        name:
                          type: string
              responses:
                '201':
                  description: Created
        components:
          securitySchemes:
            oauth:
              type: oauth2
              flows:
                clientCredentials:
                  tokenUrl: https://auth.example.com/token
                  scopes:
                    read: Read access
            bearerAuth:
              type: http
              scheme: bearer
        """
    ).strip()
    fpath = tmp_path / "openapi.yaml"
    fpath.write_text(content)
    return fpath


@pytest.fixture()
def cli_app():
    from cli import app  # type: ignore
    return app
