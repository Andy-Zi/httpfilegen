import json
from prance import ResolvingParser
from openapi_pydantic import parse_obj


def generate_http_request(path, method, spec_data):
    """Generate an HTTP request string for a given path and method."""
    full_url = (
        f"https://api.example.com{path}"  # Replace with base URL from spec if available
    )
    request_lines = [f"{method.upper()} {full_url}"]

    # Add headers
    request_lines.append("Content-Type: application/json")
    request_lines.append("Accept: application/json")

    # Handle path parameters (placeholders)
    if "parameters" in spec_data:
        for param in spec_data["parameters"]:
            if param["in"] == "path":
                placeholder = f"{{{param['name']}}}"
                full_url = full_url.replace(
                    placeholder, f"{{{param['name']}}}"
                )  # Keep as placeholder

    # Handle query parameters (example values)
    query_params = []
    if "parameters" in spec_data:
        for param in spec_data["parameters"]:
            if param["in"] == "query":
                example = param.get("example", f"{{{param['name']}}}")
                query_params.append(f"{param['name']}={example}")
    if query_params:
        full_url += "?" + "&".join(query_params)
        request_lines[0] = f"{method.upper()} {full_url}"

    # Handle request body (sample JSON)
    if "requestBody" in spec_data and "content" in spec_data["requestBody"]:
        content = spec_data["requestBody"]["content"]
        if "application/json" in content:
            schema = content["application/json"].get("schema", {})
            example = schema.get("example", {"key": "value"})  # Fallback example
            request_lines.append("")
            request_lines.append(json.dumps(example, indent=2))

    return "\n".join(request_lines)


def convert_openapi_to_http(spec_file, output_file):
    """Convert OpenAPI spec to HTTP file."""
    parser = ResolvingParser(spec_file)
    spec = parser.specification
    openapi_model = parse_obj(spec)

    with open(output_file, 'w') as f:
        for path, methods in spec.get('paths', {}).items():
            for method, details in methods.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    http_request = generate_http_request(path, method, details)
                    f.write(http_request + "\n\n###\n\n")
