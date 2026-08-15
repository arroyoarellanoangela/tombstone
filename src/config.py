"""Runtime configuration. The only place environment variables are read."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str
    tracking_window_days: int = 90
    run_budget_usd: float = 15.00
    max_verification_rounds: int = 2


settings = Settings()
