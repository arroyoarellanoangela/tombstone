"""Runtime configuration. The only place environment variables are read."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Empty by default rather than required, because most of what this repo
    # does needs no key at all: the test suite injects fake agent callers and
    # never reaches the network, `make dev` serves the committed snapshot, and
    # the dashboard's static build has no backend behind it. Making the key
    # mandatory at import time meant none of that could run without one --
    # CI could not even collect the tests. The key is demanded at the one
    # point it is genuinely needed, when an agent call is about to be spawned
    # (see utils/llm.py), where a missing one stops the run with a message
    # that says what to do about it.
    anthropic_api_key: str = ""
    tracking_window_days: int = 90
    run_budget_usd: float = 15.00
    max_verification_rounds: int = 2


settings = Settings()
