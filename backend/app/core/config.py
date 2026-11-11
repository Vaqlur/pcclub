"""Application settings, loaded from environment variables and backend/.env."""

from datetime import time
from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET = "dev-only-insecure-secret-change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["dev", "test", "prod"] = "dev"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pcclub"
    test_database_url: str | None = None

    # --- secrets (dev defaults are rejected when environment == "prod") ---
    jwt_secret: str = _DEV_SECRET
    iin_hash_pepper: str = _DEV_SECRET
    iin_encryption_key: str = ""  # Fernet key; empty = derived dev key
    mock_payment_webhook_secret: str = _DEV_SECRET

    # --- auth ---
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 30
    otp_ttl_seconds: int = 300
    otp_resend_cooldown_seconds: int = 60
    otp_max_attempts: int = 5
    otp_fixed_code: str | None = None  # mock SMS only; ignored in prod

    # --- integrations ---
    identity_provider: str = "mock"
    sms_provider: str = "mock"
    payment_provider_card: str = "mock"
    payment_provider_kaspi: str = "mock"

    # --- CORS: only browsers need it (Expo web preview, admin panel); native apps do not ---
    # Regex of allowed origins. None = localhost-only in dev, disabled in test and prod.
    cors_allow_origin_regex: str | None = None

    # --- booking rules ---
    booking_hold_minutes: int = 10
    slot_minutes: int = 30
    min_booking_minutes: int = 60
    max_booking_minutes: int = 12 * 60
    max_advance_days: int = 14

    # --- age rule: minors may not book/play in [night_start, night_end) club-local ---
    adult_age: int = 18
    night_start: time = time(22, 0)
    night_end: time = time(6, 0)

    @model_validator(mode="after")
    def _no_dev_secrets_in_prod(self) -> Self:
        if self.environment == "prod":
            weak = [
                name
                for name in ("jwt_secret", "iin_hash_pepper")
                if getattr(self, name) == _DEV_SECRET
            ]
            if not self.iin_encryption_key:
                weak.append("iin_encryption_key")
            if len(self.jwt_secret) < 32:
                weak.append("jwt_secret (min 32 characters)")
            if weak:
                raise ValueError(f"production requires real secrets for: {', '.join(weak)}")
            if self.otp_fixed_code:
                raise ValueError("OTP_FIXED_CODE must not be set in production")
        return self

    @property
    def uses_mock_payments(self) -> bool:
        return "mock" in (self.payment_provider_card, self.payment_provider_kaspi)


@lru_cache
def get_settings() -> Settings:
    return Settings()
