"""Tests for error handling in http_file_generator."""

import pytest
import json
from pathlib import Path
from http_file_generator.http_file_generator import _parse_spec_content, load_data


class TestParseSpecContent:
    """Tests for _parse_spec_content function."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON content."""
        content = '{"openapi": "3.0.0", "info": {"title": "Test"}}'
        result = _parse_spec_content(content)
        assert result["openapi"] == "3.0.0"
        assert result["info"]["title"] == "Test"

    def test_parse_valid_yaml(self):
        """Test parsing valid YAML content."""
        content = """
openapi: "3.0.0"
info:
  title: Test API
"""
        result = _parse_spec_content(content)
        assert result["openapi"] == "3.0.0"
        assert result["info"]["title"] == "Test API"

    def test_parse_invalid_json_valid_yaml(self):
        """Test that invalid JSON falls back to YAML parsing."""
        # This is valid YAML but not valid JSON
        content = "key: value\nlist:\n  - item1\n  - item2"
        result = _parse_spec_content(content)
        assert result["key"] == "value"
        assert result["list"] == ["item1", "item2"]

    def test_parse_invalid_content_raises_error(self):
        """Test that invalid content raises ValueError with details."""
        content = "{{{{invalid json and yaml"
        with pytest.raises(ValueError) as exc_info:
            _parse_spec_content(content)
        # Should include both JSON and YAML error info
        assert "Failed to parse spec content" in str(exc_info.value)


class TestLoadData:
    """Tests for load_data function."""

    def test_load_from_path(self, tmp_path):
        """Test loading spec from a Path object."""
        spec_file = tmp_path / "spec.json"
        spec_content = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {},
        }
        spec_file.write_text(json.dumps(spec_content))

        result = load_data(spec_file)
        assert result["info"]["title"] == "Test"

    def test_load_from_string_path(self, tmp_path):
        """Test loading spec from a string path."""
        spec_file = tmp_path / "spec.yaml"
        spec_content = """
openapi: "3.0.0"
info:
  title: YAML Test
  version: "1.0"
paths: {}
"""
        spec_file.write_text(spec_content)

        result = load_data(str(spec_file))
        assert result["info"]["title"] == "YAML Test"

    def test_load_nonexistent_file_raises_error(self):
        """Test that loading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_data(Path("/nonexistent/path/spec.json"))

    def test_load_invalid_spec_raises_validation_error(self, tmp_path):
        """Test that invalid OpenAPI spec raises ValueError."""
        spec_file = tmp_path / "invalid.json"
        # Missing required fields
        spec_file.write_text('{"not": "a valid openapi spec"}')

        with pytest.raises((ValueError, Exception)):
            load_data(spec_file)


class TestLoadDataUrlHandling:
    """Tests for URL handling in load_data (mocked)."""

    def test_invalid_url_treated_as_file_path(self, tmp_path):
        """Test that invalid URL-like strings are treated as file paths."""
        # String that doesn't match URL pattern
        spec_file = tmp_path / "local-spec.json"
        spec_content = {
            "openapi": "3.0.0",
            "info": {"title": "Local", "version": "1.0"},
            "paths": {},
        }
        spec_file.write_text(json.dumps(spec_content))

        # Should treat as local file path
        result = load_data(str(spec_file))
        assert result["info"]["title"] == "Local"
