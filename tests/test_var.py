"""Tests for HttpVariable and BaseURL classes."""

from http_file_generator.models.http_file.var import HttpVariable, BaseURL


class TestHttpVariable:
    """Tests for HttpVariable class."""

    def test_str_with_value_and_description(self):
        """Test __str__ with value and single-line description."""
        var = HttpVariable(name="api_key", value="secret123", description="API key")
        result = str(var)
        assert "# API key" in result
        assert "@api_key=secret123" in result

    def test_str_with_value_no_description(self):
        """Test __str__ with value but no description."""
        var = HttpVariable(name="token", value="abc123", description="")
        result = str(var)
        assert "@token=abc123" in result
        assert "#" not in result.split("@")[0]  # No comment before the variable

    def test_str_with_multiline_description(self):
        """Test __str__ with multi-line description."""
        var = HttpVariable(
            name="user_id",
            value="42",
            description="The user identifier.\nMust be a positive integer.",
        )
        result = str(var)
        assert "# The user identifier." in result
        assert "# Must be a positive integer." in result
        assert "@user_id=42" in result

    def test_str_without_value_prompt_variable(self):
        """Test __str__ without value creates a prompt variable."""
        var = HttpVariable(name="password", value="", description="Enter password")
        result = str(var)
        assert "# Enter password" in result
        assert "# @promptpassword" in result
        assert "@password=" not in result

    def test_str_without_value_no_description(self):
        """Test __str__ without value and no description."""
        var = HttpVariable(name="secret", value="", description="")
        result = str(var)
        assert "# @promptsecret" in result

    def test_hash(self):
        """Test that HttpVariable is hashable."""
        var1 = HttpVariable(name="test", value="value1", description="desc")
        var2 = HttpVariable(name="test", value="value1", description="different")
        var3 = HttpVariable(name="test", value="value2", description="desc")

        # Same name and value should have same hash (description not included)
        assert hash(var1) == hash(var2)
        # Different value should have different hash
        assert hash(var1) != hash(var3)

    def test_hashable_in_set(self):
        """Test that HttpVariable can be used in a set."""
        var1 = HttpVariable(name="test", value="value", description="")
        var2 = HttpVariable(name="other", value="value", description="")

        var_set = {var1, var2}
        assert len(var_set) == 2
        # Can add to set without error
        var_set.add(HttpVariable(name="third", value="val", description=""))
        assert len(var_set) == 3


class TestBaseURL:
    """Tests for BaseURL class."""

    def test_default_name(self):
        """Test that BaseURL has default name of BASE_URL."""
        url = BaseURL(value="https://api.example.com", description="Production API")
        assert url.name == "BASE_URL"

    def test_str_output(self):
        """Test BaseURL string output."""
        url = BaseURL(value="https://api.example.com", description="API endpoint")
        result = str(url)
        assert "# API endpoint" in result
        assert "@BASE_URL=https://api.example.com" in result

    def test_hashable(self):
        """Test that BaseURL is hashable and can be used in sets."""
        url1 = BaseURL(value="https://api1.example.com", description="")
        url2 = BaseURL(value="https://api2.example.com", description="")

        url_set = {url1, url2}
        assert len(url_set) == 2

    def test_custom_name_override(self):
        """Test that BaseURL name can be overridden if needed."""
        url = BaseURL(name="CUSTOM_URL", value="https://custom.example.com", description="")
        assert url.name == "CUSTOM_URL"
        assert "@CUSTOM_URL=https://custom.example.com" in str(url)
