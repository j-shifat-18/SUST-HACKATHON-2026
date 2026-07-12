"""
Application settings via pydantic-settings.
Reads from .env file in the liquidity-intelligence/ root.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "MFS Liquidity Intelligence"
    app_env: str = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    # --- Database (Supabase via Prisma) ---
    database_url: str = ""
    direct_url: str = ""

    # --- Supabase ---
    supabase_url: str = ""
    supabase_key: str = ""

    # --- OpenAI ---
    openai_api_key: str = ""

    # --- Firebase ---
    firebase_project_id: str = ""
    firebase_client_email: str = ""
    firebase_private_key: str = ""

    # --- JWT ---
    jwt_secret: str = ""

    # --- Engine parameters ---
    low_liquidity_threshold_pct: float = 20.0
    critical_liquidity_threshold_pct: float = 10.0
    anomaly_zscore_threshold: float = 2.5
    anomaly_rolling_window_hours: int = 24
    forecast_horizon_hours: int = 12


@lru_cache()
def get_settings() -> Settings:
    return Settings()
