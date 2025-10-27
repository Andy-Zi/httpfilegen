from os import stat
from pathlib import Path
from prance import ResolvingParser
from openapi_pydantic import (
    OpenAPI,
    Server,
    PathItem,
    Parameter,
    Response,
    parse_obj,
)
from pydantic import BaseModel, field_validator
from jsf import JSF
from faker.providers import BaseProvider


class Duration_provider(BaseProvider):
    def duration(self):
        return self.generator.time_delta()


class OpenApiParser(BaseModel):
    path: Path
    model: OpenAPI

    def __init__(self, path: Path):
        model = parse_obj(ResolvingParser(path.as_posix()).specification)
        super().__init__(path=path, model=model)

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

    def get_sample_for_path(self, path: str) -> dict[str, dict | None]:
        """return a sample example for the request body of the path's operations"""
        path_item = self.get_path_item(path)
        samples = {}
        methods = [m for m in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head', 'trace'] if getattr(path_item, m, None) is not None]
        for method in methods:
            operation = getattr(path_item, method)
            if operation.requestBody and operation.requestBody.content:
                # Get the first content type's example
                content = next(iter(operation.requestBody.content.values()))
                if content.example:
                    samples[method] = content.example
                elif content.examples:
                    # Return the first example's value
                    first_example = next(iter(content.examples.values()))
                    if hasattr(first_example, "value"):
                        samples[method] = first_example.value
                else:
                    samples[method] = None
            else:
                samples[method] = None
        return samples

    def get_path_params(self, path: str) -> dict[str, list[Parameter]]:
        """return all path parameters for the given path for all methods"""
        path_item = self.get_path_item(path)
        params_dict = {}
        methods = [m for m in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head', 'trace'] if getattr(path_item, m, None) is not None]
        for method in methods:
            params = []
            if path_item.parameters:
                params.extend(
                    [
                        p
                        for p in path_item.parameters
                        if isinstance(p, Parameter) and p.param_in == "path"
                    ]
                )
            operation = getattr(path_item, method)
            if operation.parameters:
                params.extend(
                    [
                        p
                        for p in operation.parameters
                        if isinstance(p, Parameter) and p.param_in == "path"
                    ]
                )
            params_dict[method] = params
        return params_dict

    def get_query_params(self, path: str) -> dict[str, list[Parameter]]:
        """return all query parameters for the given path for all methods"""
        path_item = self.get_path_item(path)
        params_dict = {}
        methods = [m for m in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head', 'trace'] if getattr(path_item, m, None) is not None]
        for method in methods:
            params = []
            if path_item.parameters:
                params.extend(
                    [
                        p
                        for p in path_item.parameters
                        if isinstance(p, Parameter) and p.param_in == "query"
                    ]
                )
            operation = getattr(path_item, method)
            if operation.parameters:
                params.extend(
                    [
                        p
                        for p in operation.parameters
                        if isinstance(p, Parameter) and p.param_in == "query"
                    ]
                )
            params_dict[method] = params
        return params_dict

    def get_request_body(
        self, path: str
    ) -> dict[str, dict[str, dict] | None]:
        """return a sample dict for the request body schema of the given path for all methods"""
        path_item = self.get_path_item(path)
        requests_dict = {}
        methods = [m for m in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head', 'trace'] if getattr(path_item, m, None) is not None]
        for method in methods:
            operation = getattr(path_item, method)
            if operation.requestBody:
                requests: dict[str, dict] = {}
                for content_type in operation.requestBody.content:
                    schema = operation.requestBody.content.get(
                        content_type, {}
                    ).media_type_schema.dict(by_alias=True, exclude_none=True)
                    if schema:
                        requests[content_type] = self._generate_sample_from_schema(schema)
                if requests:
                    requests_dict[method] = requests
                else:
                    requests_dict[method] = None
            else:
                requests_dict[method] = None
        return requests_dict

    def get_response_body(
        self, path: str
    ) -> dict[str, dict[str, dict[str, dict] | None]]:
        """return the responses for the given path for all methods and statuses"""
        path_item = self.get_path_item(path)
        responses_dict = {}
        methods = [m for m in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head', 'trace'] if getattr(path_item, m, None) is not None]
        for method in methods:
            operation = getattr(path_item, method)
            if operation.responses:
                method_responses = {}
                for status in operation.responses:
                    responses: dict[str, dict] = {}
                    for content_type in operation.responses[status].content:
                        schema = (
                            operation.responses[status]
                            .content.get(content_type, {})
                            .media_type_schema.dict(by_alias=True, exclude_none=True)
                        )
                        if schema:
                            responses[content_type] = self._generate_sample_from_schema(schema)
                    if responses:
                        method_responses[status] = responses
                    else:
                        method_responses[status] = None
                responses_dict[method] = method_responses
            else:
                responses_dict[method] = {}
        return responses_dict

    def _generate_sample_from_schema(self, schema: dict) -> dict:
        """Generate a sample dict conforming to the given JSON schema using jsf."""
        try:
            faker = JSF(schema=schema)
            sample = faker.generate()
            return sample
        except Exception as e:
            raise ValueError(f"Failed to generate sample from schema: {e}")

    @field_validator("path")
    def path_must_exist(cls, v):
        if not Path(v).exists():
            raise ValueError("must exist")
        return v
