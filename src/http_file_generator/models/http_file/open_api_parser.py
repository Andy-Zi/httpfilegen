import json
from pathlib import Path
from typing import Any, Union

from openapi_pydantic.v3.parser import OpenAPIv3
from openapi_pydantic import (
    Server,
    PathItem,
    Parameter,
    parse_obj,
)
from pydantic import BaseModel
from jsf import JSF

from ..enums import METHOD


def _parse_spec_content(content: str) -> Any:
    """Parse content as JSON first, then try YAML if JSON fails."""
    import json

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            import yaml

            return yaml.safe_load(content)
        except ImportError:
            raise ValueError(
                "YAML support not available. Install PyYAML to parse YAML files."
            )
        except Exception:
            raise ValueError("Content is neither valid JSON nor YAML")


def _load_spec_data(file: Path | str) -> Any:
    """Load and parse OpenAPI spec from file or URL."""
    import urllib.request
    from urllib.parse import urlparse

    if isinstance(file, Path):
        content = Path(file).read_text()
        data = _parse_spec_content(content)
    else:
        parsed = urlparse(file)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            try:
                with urllib.request.urlopen(file) as resp:
                    charset = resp.headers.get_content_charset() or "utf-8"
                    content = resp.read().decode(charset)
                data = _parse_spec_content(content)
            except Exception as e:
                raise ValueError(
                    f"Failed to download or parse OpenAPI from URL '{file}': {e}"
                )
        else:
            # Treat as a local file path string
            content = Path(file).read_text()
            data = _parse_spec_content(content)

    from prance import ResolvingParser, ValidationError

    try:
        return ResolvingParser(spec_string=json.dumps(data)).specification
    except ValidationError:
        major, minor, patch = data.get("openapi").split(".")
        if int(major) == 3 and (int(minor) > 0 or int(patch) > 0):
            data["openapi"] = "3.1.0"
            return ResolvingParser(spec_string=json.dumps(data)).specification


class OpenApiParser(BaseModel):
    model: OpenAPIv3

    def __init__(self, data: Union[dict, str, Path]) -> None:
        if isinstance(data, (str, Path)):
            # Load data from file/URL
            parsed_data = _load_spec_data(data)
        else:
            # Data is already parsed
            parsed_data = data
        model = parse_obj(parsed_data)
        super().__init__(model=model)

    def get_paths(self) -> list[str]:
        """return all paths"""
        if self.model.paths is None:
            return []
        return list(self.model.paths.keys())

    def get_server(self) -> list[Server]:
        """return all servers"""
        return self.model.servers

    def get_path_item(self, path: str) -> PathItem:
        """return the PathItem for the given path"""
        if self.model.paths is None:
            raise ValueError(f"Path '{path}' not found: paths is None")
        return self.model.paths[path]

    def get_sample_for_path(self, path: str) -> dict[str, Any | None]:
        """return a sample example for the request body of the path's operations"""
        path_item = self.get_path_item(path)
        samples = {}
        methods = [m for m in METHOD if getattr(path_item, m.lower(), None) is not None]
        for method in methods:
            method_name = method.value
            operation = getattr(path_item, method_name.lower())
            if operation.requestBody and operation.requestBody.content:
                # Get the first content type's example
                content = next(iter(operation.requestBody.content.values()))
                if content.example:
                    samples[method_name] = content.example
                elif content.examples:
                    # Return the first example's value
                    first_example = next(iter(content.examples.values()))
                    if hasattr(first_example, "value"):
                        samples[method_name] = first_example.value
                    elif isinstance(first_example, dict):
                        samples[method_name] = first_example
                else:
                    samples[method_name] = None
            else:
                samples[method_name] = None
        return samples

    def get_path_params(self, path: str) -> dict[str, list[Parameter]]:
        """return all path parameters for the given path for all methods"""
        path_item = self.get_path_item(path)
        params_dict = {}
        methods = [m for m in METHOD if getattr(path_item, m.lower(), None) is not None]
        for method in methods:
            method_name = method.value
            params = []
            if path_item.parameters:
                params.extend(
                    [
                        p
                        for p in path_item.parameters
                        if isinstance(p, Parameter) and p.param_in == "path"
                    ]
                )
            operation = getattr(path_item, method_name.lower())
            if operation.parameters:
                params.extend(
                    [
                        p
                        for p in operation.parameters
                        if isinstance(p, Parameter) and p.param_in == "path"
                    ]
                )
            params_dict[method_name] = params
        return params_dict

    def get_query_params(self, path: str) -> dict[str, list[Parameter]]:
        """return all query parameters for the given path for all methods"""
        path_item = self.get_path_item(path)
        params_dict = {}
        methods = [m for m in METHOD if getattr(path_item, m.lower(), None) is not None]
        for method in methods:
            method_name = method.value
            params = []
            if path_item.parameters:
                params.extend(
                    [
                        p
                        for p in path_item.parameters
                        if isinstance(p, Parameter) and p.param_in == "query"
                    ]
                )
            operation = getattr(path_item, method_name.lower())
            if operation.parameters:
                params.extend(
                    [
                        p
                        for p in operation.parameters
                        if isinstance(p, Parameter) and p.param_in == "query"
                    ]
                )
            params_dict[method_name] = params
        return params_dict

    def get_request_body(self, path: str) -> dict[str, dict[str, dict] | None]:
        """return a sample dict for the request body schema of the given path for all methods"""
        path_item = self.get_path_item(path)
        requests_dict = {}
        methods = [m for m in METHOD if getattr(path_item, m.lower(), None) is not None]
        for method in methods:
            method_name = method.value
            operation = getattr(path_item, method_name.lower())
            if operation.requestBody:
                requests: dict[str, dict] = {}
                content_map = getattr(operation.requestBody, "content", None) or {}
                for content_type, media in content_map.items():
                    # Prefer example/examples if present
                    if getattr(media, "example", None) is not None:
                        requests[content_type] = media.example
                        continue
                    if getattr(media, "examples", None):
                        first = next(iter(media.examples.values()))
                        if hasattr(first, "value"):
                            requests[content_type] = first.value
                        elif isinstance(first, dict):
                            requests[content_type] = first
                        else:
                            requests[content_type] = None
                        continue
                    schema = getattr(media, "media_type_schema", None)
                    if schema is not None:
                        schema_dict = schema.model_dump(
                            by_alias=True, exclude_none=True
                        )
                        if schema_dict:
                            requests[content_type] = self._generate_sample_from_schema(
                                schema_dict
                            )
                requests_dict[method_name] = requests or None
            else:
                requests_dict[method_name] = None
        return requests_dict

    def get_response_body(
        self, path: str
    ) -> dict[str, dict[str, dict[str, dict] | None]]:
        """return the responses for the given path for all methods and statuses"""
        path_item = self.get_path_item(path)
        responses_dict = {}
        methods = [m for m in METHOD if getattr(path_item, m.lower(), None) is not None]
        for method in methods:
            method_name = method.value
            operation = getattr(path_item, method_name.lower())
            if operation.responses:
                method_responses: dict[str, dict[str, dict] | None] = {}
                for status, response in operation.responses.items():
                    responses: dict[str, dict] = {}
                    content_map = getattr(response, "content", None) or {}
                    for content_type, media in content_map.items():
                        # Prefer example/examples if present
                        if getattr(media, "example", None) is not None:
                            responses[content_type] = media.example
                            continue
                        if getattr(media, "examples", None):
                            first = next(iter(media.examples.values()))
                            if hasattr(first, "value"):
                                responses[content_type] = first.value
                            elif isinstance(first, dict):
                                responses[content_type] = first
                            else:
                                responses[content_type] = None
                            continue
                        schema = getattr(media, "media_type_schema", None)
                        if schema is not None:
                            schema_dict = schema.model_dump(
                                by_alias=True, exclude_none=True
                            )
                            if schema_dict:
                                responses[content_type] = (
                                    self._generate_sample_from_schema(schema_dict)
                                )
                    method_responses[status] = responses or None
                responses_dict[method_name] = method_responses
            else:
                responses_dict[method_name] = {}
        return responses_dict

    def _generate_sample_from_schema(self, schema: dict) -> dict:
        """Generate a sample dict conforming to the given JSON schema using jsf."""
        try:
            faker = JSF(schema=schema)
            sample = faker.generate()
            return sample
        except Exception as e:
            raise ValueError(f"Failed to generate sample from schema: {e}")
