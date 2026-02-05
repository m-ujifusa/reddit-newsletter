from pathlib import Path
from functools import lru_cache
from typing import Any, Dict

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "newsletter-bot/0.1"

    # Anthropic
    anthropic_api_key: str = ""

    # Database
    database_url: str = Field(default=f"sqlite:///{PROJECT_ROOT / 'newsletter.db'}")

    # Email (deferred)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""

    # Web
    web_host: str = "0.0.0.0"
    web_port: int = 8000


def _load_yaml(path: Path) -> Dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_subreddit_config() -> Dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "subreddits.yaml")


@lru_cache
def get_newsletter_config() -> Dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "newsletter.yaml")
