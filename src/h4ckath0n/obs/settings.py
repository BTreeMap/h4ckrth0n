"""Environment-driven observability settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilitySettings(BaseSettings):
    """Observability configuration. Off by default."""

    model_config = SettingsConfigDict(extra="ignore")

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "default"
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = ""
