"""Configuration settings for Semantic Scholar MCP server."""

import os


class Settings:
    """Configuration settings loaded from environment variables.

    Attributes:
        api_key: Optional Semantic Scholar API key for higher rate limits.
        graph_api_base_url: Base URL for the Graph API.
        recommendations_api_base_url: Base URL for the Recommendations API.
    """

    def __init__(self) -> None:
        self.api_key: str | None = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        self.graph_api_base_url: str = "https://api.semanticscholar.org/graph/v1"
        self.recommendations_api_base_url: str = (
            "https://api.semanticscholar.org/recommendations/v1"
        )
        self.disable_ssl_verify: bool = (
            os.environ.get("DISABLE_SSL_VERIFY", "").lower() in ("true", "1", "yes")
        )

    @property
    def has_api_key(self) -> bool:
        """Check if an API key is configured."""
        return self.api_key is not None and len(self.api_key) > 0


settings = Settings()
