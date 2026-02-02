"""Tests for configuration settings and environment variable handling."""

import os
from unittest.mock import patch

import pytest

from semantic_scholar_mcp.config import Settings


class TestDefaultConfiguration:
    """Tests for default configuration values."""

    def test_default_api_key_is_none(self) -> None:
        """Test that API key defaults to None when not set."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.api_key is None

    def test_default_graph_api_base_url(self) -> None:
        """Test default Graph API base URL."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.graph_api_base_url == "https://api.semanticscholar.org/graph/v1"

    def test_default_recommendations_api_base_url(self) -> None:
        """Test default Recommendations API base URL."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert (
                settings.recommendations_api_base_url
                == "https://api.semanticscholar.org/recommendations/v1"
            )

    def test_default_retry_configuration(self) -> None:
        """Test default retry configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.retry_max_attempts == 5
            assert settings.retry_base_delay == 1.0
            assert settings.retry_max_delay == 60.0
            assert settings.enable_auto_retry is True

    def test_default_logging_configuration(self) -> None:
        """Test default logging configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.log_level == "INFO"
            assert settings.log_format == "simple"

    def test_default_circuit_breaker_configuration(self) -> None:
        """Test default circuit breaker configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.circuit_failure_threshold == 5
            assert settings.circuit_recovery_timeout == 30.0

    def test_default_cache_configuration(self) -> None:
        """Test default cache configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.cache_enabled is True
            assert settings.cache_ttl == 300
            assert settings.cache_paper_ttl == 3600

    def test_default_ssl_verify_enabled(self) -> None:
        """Test that SSL verification is enabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.disable_ssl_verify is False


class TestEnvironmentVariableLoading:
    """Tests for environment variable loading."""

    def test_api_key_loaded_from_environment(self) -> None:
        """Test that API key is loaded from SEMANTIC_SCHOLAR_API_KEY."""
        with patch.dict(os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "test-key-123"}):
            settings = Settings()
            assert settings.api_key == "test-key-123"

    def test_retry_max_attempts_from_environment(self) -> None:
        """Test loading retry max attempts from environment."""
        with patch.dict(os.environ, {"SS_RETRY_MAX_ATTEMPTS": "10"}):
            settings = Settings()
            assert settings.retry_max_attempts == 10

    def test_retry_base_delay_from_environment(self) -> None:
        """Test loading retry base delay from environment."""
        with patch.dict(os.environ, {"SS_RETRY_BASE_DELAY": "2.5"}):
            settings = Settings()
            assert settings.retry_base_delay == 2.5

    def test_retry_max_delay_from_environment(self) -> None:
        """Test loading retry max delay from environment."""
        with patch.dict(os.environ, {"SS_RETRY_MAX_DELAY": "120.0"}):
            settings = Settings()
            assert settings.retry_max_delay == 120.0

    def test_enable_auto_retry_false_from_environment(self) -> None:
        """Test disabling auto retry via environment."""
        with patch.dict(os.environ, {"SS_ENABLE_AUTO_RETRY": "false"}):
            settings = Settings()
            assert settings.enable_auto_retry is False

    def test_log_level_from_environment(self) -> None:
        """Test loading log level from environment."""
        with patch.dict(os.environ, {"SS_LOG_LEVEL": "DEBUG"}):
            settings = Settings()
            assert settings.log_level == "DEBUG"

    def test_log_format_from_environment(self) -> None:
        """Test loading log format from environment."""
        with patch.dict(os.environ, {"SS_LOG_FORMAT": "detailed"}):
            settings = Settings()
            assert settings.log_format == "detailed"

    def test_circuit_failure_threshold_from_environment(self) -> None:
        """Test loading circuit failure threshold from environment."""
        with patch.dict(os.environ, {"SS_CIRCUIT_FAILURE_THRESHOLD": "10"}):
            settings = Settings()
            assert settings.circuit_failure_threshold == 10

    def test_circuit_recovery_timeout_from_environment(self) -> None:
        """Test loading circuit recovery timeout from environment."""
        with patch.dict(os.environ, {"SS_CIRCUIT_RECOVERY_TIMEOUT": "60.0"}):
            settings = Settings()
            assert settings.circuit_recovery_timeout == 60.0

    def test_cache_enabled_false_from_environment(self) -> None:
        """Test disabling cache via environment."""
        with patch.dict(os.environ, {"SS_CACHE_ENABLED": "false"}):
            settings = Settings()
            assert settings.cache_enabled is False

    def test_cache_ttl_from_environment(self) -> None:
        """Test loading cache TTL from environment."""
        with patch.dict(os.environ, {"SS_CACHE_TTL": "600"}):
            settings = Settings()
            assert settings.cache_ttl == 600

    def test_cache_paper_ttl_from_environment(self) -> None:
        """Test loading cache paper TTL from environment."""
        with patch.dict(os.environ, {"SS_CACHE_PAPER_TTL": "7200"}):
            settings = Settings()
            assert settings.cache_paper_ttl == 7200

    def test_disable_ssl_verify_true_from_environment(self) -> None:
        """Test disabling SSL verification via environment."""
        with patch.dict(os.environ, {"DISABLE_SSL_VERIFY": "true"}):
            settings = Settings()
            assert settings.disable_ssl_verify is True

    def test_disable_ssl_verify_with_value_1(self) -> None:
        """Test disabling SSL verification with value '1'."""
        with patch.dict(os.environ, {"DISABLE_SSL_VERIFY": "1"}):
            settings = Settings()
            assert settings.disable_ssl_verify is True

    def test_disable_ssl_verify_with_value_yes(self) -> None:
        """Test disabling SSL verification with value 'yes'."""
        with patch.dict(os.environ, {"DISABLE_SSL_VERIFY": "yes"}):
            settings = Settings()
            assert settings.disable_ssl_verify is True


class TestApiKeyPresenceHandling:
    """Tests for API key presence detection."""

    def test_has_api_key_true_when_set(self) -> None:
        """Test has_api_key returns True when API key is set."""
        with patch.dict(os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "valid-key"}):
            settings = Settings()
            assert settings.has_api_key is True

    def test_has_api_key_false_when_none(self) -> None:
        """Test has_api_key returns False when API key is None."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.has_api_key is False

    def test_has_api_key_false_when_empty_string(self) -> None:
        """Test has_api_key returns False when API key is empty string."""
        with patch.dict(os.environ, {"SEMANTIC_SCHOLAR_API_KEY": ""}):
            settings = Settings()
            assert settings.has_api_key is False


class TestApiKeyWhitespaceHandling:
    """Tests for API key whitespace stripping."""

    def test_api_key_leading_whitespace_stripped(self) -> None:
        """Test that leading whitespace is stripped from API key."""
        with patch.dict(os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "  my-api-key"}):
            settings = Settings()
            assert settings.api_key == "my-api-key"

    def test_api_key_trailing_whitespace_stripped(self) -> None:
        """Test that trailing whitespace is stripped from API key."""
        with patch.dict(os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "my-api-key  "}):
            settings = Settings()
            assert settings.api_key == "my-api-key"

    def test_api_key_both_ends_whitespace_stripped(self) -> None:
        """Test that whitespace on both ends is stripped from API key."""
        with patch.dict(os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "  my-api-key  "}):
            settings = Settings()
            assert settings.api_key == "my-api-key"

    def test_api_key_whitespace_only_returns_none(self) -> None:
        """Test that whitespace-only API key is treated as None."""
        with patch.dict(os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "   "}):
            settings = Settings()
            assert settings.api_key is None

    def test_api_key_tabs_stripped(self) -> None:
        """Test that tabs are stripped from API key."""
        with patch.dict(os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "\tmy-api-key\t"}):
            settings = Settings()
            assert settings.api_key == "my-api-key"

    def test_api_key_newlines_stripped(self) -> None:
        """Test that newlines are stripped from API key."""
        with patch.dict(os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "\nmy-api-key\n"}):
            settings = Settings()
            assert settings.api_key == "my-api-key"

    def test_has_api_key_false_when_whitespace_only(self) -> None:
        """Test has_api_key returns False when API key is whitespace-only."""
        with patch.dict(os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "   "}):
            settings = Settings()
            assert settings.has_api_key is False

    def test_has_api_key_true_when_key_has_surrounding_whitespace(self) -> None:
        """Test has_api_key returns True when API key has valid content with whitespace."""
        with patch.dict(os.environ, {"SEMANTIC_SCHOLAR_API_KEY": "  valid-key  "}):
            settings = Settings()
            assert settings.has_api_key is True


class TestApiKeyAbsenceHandling:
    """Tests for handling when API key is absent."""

    def test_settings_works_without_api_key(self) -> None:
        """Test that Settings can be created without API key."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            # Should not raise and should have all other defaults
            assert settings.api_key is None
            assert settings.graph_api_base_url is not None
            assert settings.recommendations_api_base_url is not None

    def test_all_features_available_without_api_key(self) -> None:
        """Test that all configuration features are available without API key."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            # All configuration options should be accessible
            assert isinstance(settings.retry_max_attempts, int)
            assert isinstance(settings.retry_base_delay, float)
            assert isinstance(settings.retry_max_delay, float)
            assert isinstance(settings.enable_auto_retry, bool)
            assert isinstance(settings.log_level, str)
            assert isinstance(settings.log_format, str)
            assert isinstance(settings.circuit_failure_threshold, int)
            assert isinstance(settings.circuit_recovery_timeout, float)
            assert isinstance(settings.cache_enabled, bool)
            assert isinstance(settings.cache_ttl, int)
            assert isinstance(settings.cache_paper_ttl, int)
            assert isinstance(settings.disable_ssl_verify, bool)


class TestBooleanEnvironmentVariableHandling:
    """Tests for boolean environment variable parsing."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("Yes", True),
            ("YES", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("", False),
            ("random", False),
        ],
    )
    def test_enable_auto_retry_boolean_parsing(self, value: str, expected: bool) -> None:
        """Test boolean parsing for enable_auto_retry setting."""
        with patch.dict(os.environ, {"SS_ENABLE_AUTO_RETRY": value}):
            settings = Settings()
            assert settings.enable_auto_retry is expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("Yes", True),
            ("YES", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("", False),
            ("random", False),
        ],
    )
    def test_cache_enabled_boolean_parsing(self, value: str, expected: bool) -> None:
        """Test boolean parsing for cache_enabled setting."""
        with patch.dict(os.environ, {"SS_CACHE_ENABLED": value}):
            settings = Settings()
            assert settings.cache_enabled is expected
