"""
Configuration settings for the Evaluator service.

This module defines Pydantic Settings classes to load configuration
from environment variables (via .env by default), providing sensible
defaults for development.
"""

from typing import List, Optional, Literal, Dict, Any

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

    # ===== QUEUE MAPPING SETTINGS =====
    # TODO: Should I put this in CelerySettings, instead?
    question_type_to_queue: Dict[str, str] = {
        "MCQ": "mcq-queue",
        "FITB": "mcq-queue",
        "MATCHING": "mcq-queue",
        "TRUE_FALSE": "mcq-queue",
        "DESCRIPTIVE": "desc-queue",
        "CODING": "coding-queue",
        "STUB_SLEEP": "desc-queue",
    }

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


class CelerySettings(BaseSettings):
    """Celery configuration loaded from environment variables.

    All fields can be overridden using environment variables with the
    "CELERY_" prefix (case-insensitive). For example:

    - CELERY_BROKER_URL
    - CELERY_RESULT_BACKEND
    - CELERY_TASK_DEFAULT_QUEUE
    - CELERY_TASK_ROUTES (JSON string for complex types)

    Notes on complex fields:
    - For `accept_content` (List[str]) and `task_routes` (Dict), set the env var
      as a JSON string, e.g.:
        CELERY_ACCEPT_CONTENT=["json"]
        CELERY_TASK_ROUTES={"celery_app.tasks.evaluation.question.*": {"queue": "prefork-queue"}}
    """

    # Broker settings
    broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL",
    )
    result_backend: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL",
    )

    # Task settings
    task_serializer: str = Field(default="json")
    accept_content: List[str] = Field(default_factory=lambda: ["json"])
    result_serializer: str = Field(default="json")
    timezone: str = Field(default="UTC")
    enable_utc: bool = Field(default=True)

    # Queue settings
    task_default_queue: str = Field(default="prefork-queue")

    # Task result settings
    result_expires: int = Field(
        default=3600, description="Seconds until results expire"
    )

    # Worker settings
    worker_prefetch_multiplier: int = Field(default=1)
    task_acks_late: bool = Field(default=True)
    worker_disable_rate_limits: bool = Field(default=True)

    # Heartbeat and events settings
    worker_heartbeat_interval: int = Field(
        default=10, description="Heartbeat interval in seconds (higher = less frequent)"
    )
    worker_enable_heartbeat: bool = Field(
        default=True, description="Enable worker heartbeat events"
    )
    worker_max_tasks_per_child: int = Field(
        default=1000, description="Max tasks before worker process is recycled"
    )

    # Logging
    worker_log_format: str = Field(
        default="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
    )
    worker_task_log_format: str = Field(
        default="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_prefix="CELERY_",
        extra="ignore",
    )

    def get_config(self) -> Dict[str, Any]:
        """Return configuration as a plain dictionary for Celery."""
        return self.model_dump()


# Global celery settings instance for easy import
celery_settings = CelerySettings()
