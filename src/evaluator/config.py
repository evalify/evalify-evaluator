"""
Configuration settings for the Evaluator service.

This module defines the Pydantic Settings class to load configuration
from environment variables, providing defaults for development.
"""

from typing import List, Optional, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# NOTE: Update .env.example when changing settings
class Settings(BaseSettings):
    """Configuration settings loaded from environment variables."""

    # ===== CORE APPLICATION SETTINGS =====

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for job state and task queue",
    )

    evalify_backend_url: str = Field(
        default="http://localhost:8020",
        description="Base URL for the main Evalify backend API",
    )

    # ===== OPTIONAL SERVER SETTINGS =====

    host: str = Field(
        default="127.0.0.1",
        description="Host address to bind the server",
    )

    port: int = Field(
        default=4040,
        description="Port number to bind the server",
    )

    environment: Literal["development", "staging", "production"] = Field(
        default="production",
        description="Environment mode: development, staging, production",
    )

    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    # ===== LOGGING SETTINGS =====

    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )

    # ===== CORS SETTINGS =====

    allowed_origins: Optional[str] = Field(
        default=None,
        description="Comma-separated list of allowed origins for CORS",
    )

    allowed_methods: str = Field(
        default="GET,POST,PUT,DELETE,OPTIONS",
        description="Comma-separated list of allowed HTTP methods",
    )

    allowed_headers: str = Field(
        default="*",
        description="Allowed headers for CORS",
    )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert allowed_origins string to list."""
        if not self.allowed_origins:
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def allowed_methods_list(self) -> List[str]:
        """Convert allowed_methods string to list."""
        return [method.strip() for method in self.allowed_methods.split(",")]


# Global settings instance for easy import
settings = Settings()
