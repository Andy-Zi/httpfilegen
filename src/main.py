from pathlib import Path
from http_file_generator import HtttpFileGenerator

samples_folder = Path("../samples/httpbin/")
if __name__ == "__main__":
    # for file in samples_folder.glob("*json"):
    # for folder in samples_folder.glob("*"):
    file = list(samples_folder.glob("*json"))
    # if not len(file) == 1: 
    #     continue
    file = file[0]
    # if not file.exists():
    #     continue
    # spec_file = Path("../samples/petstore-expanded.json")  # Input spec file
    # model = openapi_parser.OpenApiParser(file)
    # path = "/bid-manager/api/v1/workflow/"
    # paths = model.get_paths()
    # server = model.get_server()
    # path_item = model.get_path_item(path)
    # path_sample = model.get_sample_for_path(path)
    # path_item = model.get_path_item(path)
    # path_sample = model.get_sample_for_path(path)
    # path_params = model.get_path_params(path)
    # path_query_params = model.get_query_params(path)
    # path_request_body = model.get_request_body(path)
    # path_response_body = model.get_response_body(path)
    # output_file = "output.http"  # Output HTTP file
    output_file = f"{file.parent}/{file.stem}.http"
    http_file_generator = HtttpFileGenerator(file)
    http_file_generator.to_http_file(Path(output_file))
    print(f"HTTP file generated: {output_file}")
