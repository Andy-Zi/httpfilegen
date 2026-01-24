"""Tests for pre/post request script functionality."""

from http_file_generator.models.http_file.request import HttpRequest
from http_file_generator.models.http_file.scripts import HttpScript
from http_file_generator.models.enums import METHOD


class TestHttpScript:
    """Tests for HttpScript model."""

    def test_create_script(self):
        """Test creating an HttpScript."""
        script = HttpScript(script="console.log('test');")
        assert script.script == "console.log('test');"

    def test_script_with_multiline(self):
        """Test script with multiple lines."""
        script_content = """
        const data = response.body;
        client.test("status", () => {
            client.assert(response.status === 200);
        });
        """
        script = HttpScript(script=script_content)
        assert "response.body" in script.script
        assert "client.test" in script.script


class TestHttpRequestScripts:
    """Tests for pre/post scripts in HttpRequest."""

    def test_request_with_pre_script(self):
        """Test HttpRequest with pre-request script."""
        pre_script = HttpScript(script="console.log('before request');")
        request = HttpRequest(
            method=METHOD.GET,
            path="/api/test",
            pre_script=pre_script,
        )
        result = request.to_http_file(base_url="{{BASE_URL}}")
        assert "< {% console.log('before request'); %}" in result

    def test_request_with_post_script(self):
        """Test HttpRequest with post-request script (response handler)."""
        post_script = HttpScript(script="client.assert(response.status === 200);")
        request = HttpRequest(
            method=METHOD.POST,
            path="/api/data",
            post_script=post_script,
        )
        result = request.to_http_file(base_url="{{BASE_URL}}")
        assert "> {% client.assert(response.status === 200); %}" in result

    def test_request_with_both_scripts(self):
        """Test HttpRequest with both pre and post scripts."""
        pre_script = HttpScript(script="request.variables.set('timestamp', Date.now());")
        post_script = HttpScript(script="client.log(response.body);")
        request = HttpRequest(
            method=METHOD.PUT,
            path="/api/resource",
            headers={"Content-Type": "application/json"},
            body={"key": "value"},
            pre_script=pre_script,
            post_script=post_script,
        )
        result = request.to_http_file(base_url="{{BASE_URL}}")

        # Pre-script should appear before the request
        assert "< {% request.variables.set('timestamp', Date.now()); %}" in result
        # Post-script should appear after the request
        assert "> {% client.log(response.body); %}" in result
        # Request content should still be present
        assert "PUT {{BASE_URL}}/api/resource" in result
        assert "Content-Type: application/json" in result

    def test_request_without_scripts(self):
        """Test HttpRequest without any scripts."""
        request = HttpRequest(
            method=METHOD.DELETE,
            path="/api/item/123",
        )
        result = request.to_http_file(base_url="{{BASE_URL}}")
        # Should not contain script markers
        assert "< {%" not in result
        assert "> {%" not in result
        # But should still have the request
        assert "DELETE {{BASE_URL}}/api/item/123" in result

    def test_script_extraction_from_operation_no_extensions(self):
        """Test _extract_scripts returns None when no extensions present."""
        # Create a mock operation without extensions
        class MockOperation:
            model_extra = {}

        pre, post = HttpRequest._extract_scripts(MockOperation())
        assert pre is None
        assert post is None

    def test_script_extraction_from_operation_with_extensions(self):
        """Test _extract_scripts extracts scripts from extensions."""
        class MockOperation:
            model_extra = {
                "x-pre-request-script": "console.log('pre');",
                "x-post-request-script": "console.log('post');",
            }

        pre, post = HttpRequest._extract_scripts(MockOperation())
        assert pre is not None
        assert pre.script == "console.log('pre');"
        assert post is not None
        assert post.script == "console.log('post');"

    def test_script_extraction_ignores_non_string_values(self):
        """Test _extract_scripts ignores non-string extension values."""
        class MockOperation:
            model_extra = {
                "x-pre-request-script": {"not": "a string"},
                "x-post-request-script": 123,
            }

        pre, post = HttpRequest._extract_scripts(MockOperation())
        assert pre is None
        assert post is None
