"""Environment-driven configuration using pydantic-settings."""

from __future__ import annotations

import secrets
import warnings

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration. All values can be overridden via env vars prefixed ``H4CKATH0N_``."""

    model_config = SettingsConfigDict(
        env_prefix="H4CKATH0N_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- environment ---
    env: str = "development"

    # --- database ---
    database_url: str = "sqlite:///./h4ckath0n.db"

    # --- auth / JWT ---
    auth_signing_key: str = ""
    auth_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    password_reset_expire_minutes: int = 30

    # --- WebAuthn / Passkeys ---
    rp_id: str = ""
    origin: str = ""
    webauthn_ttl_seconds: int = 300
    user_verification: str = "preferred"
    attestation: str = "none"

    # --- password auth (optional extra) ---
    password_auth_enabled: bool = False

    # --- admin bootstrap ---
    bootstrap_admin_emails: list[str] = []
    first_user_is_admin: bool = False

    # --- LLM ---
    openai_api_key: str = ""

    def effective_signing_key(self) -> str:
        """Return signing key, generating an ephemeral one in dev mode."""
        if self.auth_signing_key:
            return self.auth_signing_key
        if self.env == "production":
            raise RuntimeError("H4CKATH0N_AUTH_SIGNING_KEY must be set in production mode.")
        ephemeral = secrets.token_urlsafe(32)
        warnings.warn(
            "Using an ephemeral JWT signing key. Set H4CKATH0N_AUTH_SIGNING_KEY for production.",
            UserWarning,
            stacklevel=2,
        )
        return ephemeral

    def effective_rp_id(self) -> str:
        """Return the WebAuthn relying party ID."""
        if self.rp_id:
            return self.rp_id
        if self.env == "production":
            raise RuntimeError("H4CKATH0N_RP_ID must be set in production mode.")
        warnings.warn(
            "Using 'localhost' as WebAuthn RP ID. Set H4CKATH0N_RP_ID for production.",
            UserWarning,
            stacklevel=2,
        )
        return "localhost"

    def effective_origin(self) -> str:
        """Return the expected WebAuthn origin."""
        if self.origin:
            return self.origin
        if self.env == "production":
            raise RuntimeError("H4CKATH0N_ORIGIN must be set in production mode.")
        warnings.warn(
            "Using 'http://localhost:8000' as WebAuthn origin. "
            "Set H4CKATH0N_ORIGIN for production.",
            UserWarning,
            stacklevel=2,
        )
        return "http://localhost:8000"
