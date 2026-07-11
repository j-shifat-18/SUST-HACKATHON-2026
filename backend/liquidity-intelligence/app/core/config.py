"""
Application configuration using pydantic-settings.
All values are read from environment variables / .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    app_name: str = "MFS Liquidity Intelligence"
    api_v1_prefix: str = "/api/v1"

    # Database (Supabase)
    # DATABASE_URL: pooled connection string (used by Prisma at runtime)
    # DIRECT_URL: direct (non-pooled) connection string (used by Prisma migrations)
    database_url: str = ""
    direct_url: str = ""  # same as DATABASE_URL when not using PgBouncer

    # Supabase (optional — used for storage / realtime)
    supabase_url: str = ""
    supabase_key: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Firebase
    firebase_project_id: str = ""
    firebase_client_email: str = ""
    firebase_private_key: str = ""

    # Auth / JWT fallback (for local dev without Firebase)
    jwt_secret: str = "dev-secret-change-me"

    # Redis (optional — graceful degradation if missing)
    redis_url: str = ""

    # Liquidity thresholds (% of daily float)
    low_liquidity_threshold_pct: float = 20.0
    critical_liquidity_threshold_pct: float = 10.0

    # Anomaly engine
    anomaly_zscore_threshold: float = 2.5
    anomaly_rolling_window_hours: int = 24

    # Forecast horizon in hours
    forecast_horizon_hours: int = 12


@lru_cache
def get_settings() -> Settings:
    return Settings()
