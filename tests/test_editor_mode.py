"""Tests for editor mode functionality."""

import pytest
from http_file_generator.models.settings.settings import EditorMode, HttpSettings
from http_file_generator.models.http_file.http_file_data import HttpFileData
from http_file_generator.models.http_file.var import BaseURL
from http_file_generator.models.http_file.request import HttpRequest
from http_file_generator.models.enums import METHOD


class TestEditorMode:
    """Tests for EditorMode enum and settings."""

    def test_editor_mode_values(self):
        """Test that all editor modes exist."""
        assert EditorMode.DEFAULT
        assert EditorMode.KULALA
        assert EditorMode.PYCHARM
        assert EditorMode.HTTPYAC

    def test_http_settings_default_editor_mode(self):
        """Test that HttpSettings defaults to DEFAULT editor mode."""
        settings = HttpSettings()
        assert settings.editor_mode == EditorMode.DEFAULT

    def test_http_settings_custom_editor_mode(self):
        """Test that HttpSettings accepts custom editor mode."""
        settings = HttpSettings(editor_mode=EditorMode.KULALA)
        assert settings.editor_mode == EditorMode.KULALA

        settings = HttpSettings(editor_mode=EditorMode.PYCHARM)
        assert settings.editor_mode == EditorMode.PYCHARM

        settings = HttpSettings(editor_mode=EditorMode.HTTPYAC)
        assert settings.editor_mode == EditorMode.HTTPYAC


class TestHttpFileDataEditorHeaders:
    """Tests for editor-specific headers in HttpFileData output."""

    @pytest.fixture
    def sample_http_file_data(self):
        """Create a simple HttpFileData for testing."""
        request = HttpRequest(
            method=METHOD.GET,
            path="/users",
            headers={"Accept": "application/json"},
            summary="Get users",
        )
        return HttpFileData(
            base_urls={BaseURL(value="https://api.example.com", description="")},
            requests=[request],
        )

    def test_default_mode_no_header(self, sample_http_file_data):
        """Test that DEFAULT mode produces no editor header."""
        result = sample_http_file_data.to_http_file(editor_mode=EditorMode.DEFAULT)
        # Should not have any editor-specific header
        assert "# Kulala" not in result
        assert "# JetBrains" not in result
        assert "# httpyac" not in result

    def test_kulala_mode_header(self, sample_http_file_data):
        """Test that KULALA mode produces Kulala header."""
        result = sample_http_file_data.to_http_file(editor_mode=EditorMode.KULALA)
        assert "# Kulala.nvim HTTP file" in result
        assert "github.com/mistweaverco/kulala.nvim" in result

    def test_pycharm_mode_header(self, sample_http_file_data):
        """Test that PYCHARM mode produces JetBrains header."""
        result = sample_http_file_data.to_http_file(editor_mode=EditorMode.PYCHARM)
        assert "# JetBrains HTTP Client file" in result
        assert "jetbrains.com" in result

    def test_httpyac_mode_header(self, sample_http_file_data):
        """Test that HTTPYAC mode produces httpyac header."""
        result = sample_http_file_data.to_http_file(editor_mode=EditorMode.HTTPYAC)
        assert "# httpyac HTTP file" in result
        assert "httpyac.github.io" in result

    def test_request_content_preserved_with_editor_mode(self, sample_http_file_data):
        """Test that request content is preserved regardless of editor mode."""
        for mode in EditorMode:
            result = sample_http_file_data.to_http_file(editor_mode=mode)
            assert "GET {{BASE_URL}}/users" in result
            assert "Accept: application/json" in result
