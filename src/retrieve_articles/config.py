from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(project_root() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")
    gmail_address: str = Field(validation_alias="GMAIL_ADDRESS")
    gmail_app_password: str = Field(validation_alias="GMAIL_APP_PASSWORD")
    recipient_email: Optional[str] = Field(default=None, validation_alias="RECIPIENT_EMAIL")

    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    lookback_days: int = Field(default=3, validation_alias="LOOKBACK_DAYS")
    max_candidates: int = Field(default=50, validation_alias="MAX_CANDIDATES")

    @field_validator("gmail_address", "recipient_email", mode="before")
    @classmethod
    def strip_email(cls, value: object) -> object:
        if value is None or not isinstance(value, str):
            return value
        return value.strip()

    @field_validator("gmail_app_password", mode="before")
    @classmethod
    def normalize_app_password(cls, value: object) -> object:
        if value is None or not isinstance(value, str):
            return value
        # Google displays app passwords in 4-character groups; remove spaces if copied.
        return value.strip().replace(" ", "")

    @property
    def effective_recipient(self) -> str:
        return self.recipient_email or self.gmail_address

    @property
    def interests_path(self) -> Path:
        return project_root() / "config" / "interests.yaml"

    @property
    def history_path(self) -> Path:
        return project_root() / "data" / "seen_articles.json"


def load_settings() -> Settings:
    return Settings()
