"""
config.py — Application settings

All configuration is loaded from environment variables (or a .env file).
Pydantic-settings validates types and raises a clear error on startup if
a required variable is missing or has the wrong type.

Precedence (highest → lowest):
  1. Actual environment variables (e.g. set in the shell or docker-compose env_file)
  2. Values in .env
  3. Defaults defined here
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Required ---
    BOT_TOKEN: str = ""            # Bale bot token from BotFather
    NERKH_API_TOKEN: str = ""      # Bearer token for nerkh.io; leave empty to skip Nerkh fetches

    # --- API Endpoints (rarely need changing) ---
    TGJU_URL: str = "https://call2.tgju.org/ajax.json"
    NERKH_URL: str = "https://api.nerkh.io/v1/prices/json/all"
    BALE_API_URL: str = "https://tapi.bale.ai/bot"  # Base URL; token is appended per-request

    # --- Scheduler ---
    FETCH_INTERVAL_MINUTES: int = 5  # How often (in minutes) prices are refreshed

    # --- Storage ---
    DB_PATH: str = "data/bot.db"  # Relative path to the SQLite file; directory is auto-created

    # --- Admin Panel ---
    ADMIN_PORT: int = 8080
    ADMIN_USERNAME: str = "admin"   # Change in production!
    ADMIN_PASSWORD: str = "admin"   # Change in production!

    # --- Logging ---
    LOG_LEVEL: str = "INFO"  # One of: DEBUG, INFO, WARNING, ERROR, CRITICAL

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Module-level singleton used across the entire application
settings = Settings()
