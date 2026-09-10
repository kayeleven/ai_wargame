from typing import Literal

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

DEV_DATABASE = "living_memory_dev"
TEST_DATABASE = "living_memory_test"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LM_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )
    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://living_memory:local-development-only@127.0.0.1:5432/" + DEV_DATABASE
    )
    session_secret: SecretStr
    secure_cookies: bool = False
    thread_tokens: int = Field(default=16, ge=1, le=128)
    pool_size: int = Field(default=8, ge=1, le=64)
    pool_timeout: float = Field(default=2, gt=0, le=30)
    connect_timeout: int = Field(default=3, ge=1, le=30)
    statement_timeout_ms: int = Field(default=5000, ge=1, le=60000)

    @field_validator("session_secret")
    @classmethod
    def secret_length(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32 or value.get_secret_value().startswith("replace-"):
            raise ValueError("provide a random session secret of at least 32 characters")
        return value

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
            valid = url.drivername == "postgresql+psycopg" and bool(url.database)
        except Exception:
            valid = False
        if not valid:
            raise ValueError("a PostgreSQL Psycopg database URL is required")
        return value

    @model_validator(mode="after")
    def production_cookies(self) -> "Settings":
        if self.environment == "production" and not self.secure_cookies:
            raise ValueError("production requires secure cookies")
        return self


def load_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]  # BaseSettings reads environment values.
    except ValidationError as exc:
        fields = ", ".join(".".join(map(str, e["loc"])) or "settings" for e in exc.errors())
        raise RuntimeError(f"Invalid configuration: {fields}. Check .env.example.") from None
