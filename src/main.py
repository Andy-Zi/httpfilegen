from pathlib import Path
from modules import openapi_parser

if __name__ == "__main__":
    spec_file = Path("../openapi.json")  # Input spec file
    model = openapi_parser.OpenApiParser(spec_file)
    path = '/bid-manager/api/v1/workflow/'
    paths = model.get_paths()
    server = model.get_server()
    path_item = model.get_path_item(path)
    path_sample = model.get_sample_for_path(path)
    path_item = model.get_path_item(path)
    path_sample = model.get_sample_for_path(path)
    path_params = model.get_path_params(path)
    path_query_params = model.get_query_params(path)
    path_request_body = model.get_request_body(path)
    path_response_body = model.get_response_body(path)
    output_file = "output.http"  # Output HTTP file
    convert_openapi_to_http(spec_file, output_file)
    print(f"HTTP file generated: {output_file}")
