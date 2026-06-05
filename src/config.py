from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    NERKH_API_TOKEN: str = ""
    TGJU_URL: str = "https://call2.tgju.org/ajax.json"
    NERKH_URL: str = "https://api.nerkh.io/v1/prices/json/all"
    BALE_API_URL: str = "https://tapi.bale.ai/bot"
    FETCH_INTERVAL_MINUTES: int = 5
    DB_PATH: str = "data/bot.db"
    ADMIN_PORT: int = 8080
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
