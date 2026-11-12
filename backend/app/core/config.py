from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    PROJECT_NAME: str = "SIAA API"
    VERSION: str = "1.0.0"
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    POSTGRES_DB: str
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=1440)
    SQL_ECHO: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_origins(cls, value: list[str]) -> list[str]:
        if any(origin == "*" or not origin.startswith(("http://", "https://")) for origin in value):
            raise ValueError("CORS requiere orígenes HTTP(S) explícitos")
        return value

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if "cambiar" in value.lower() or len(set(value)) < 8:
            raise ValueError("Genera una SECRET_KEY aleatoria de al menos 32 caracteres")
        return value

    @field_validator("ALGORITHM")
    @classmethod
    def validate_algorithm(cls, value: str) -> str:
        if value != "HS256":
            raise ValueError("Este backend utiliza HS256")
        return value

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return URL.create(
            "postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)

    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore")


settings = Settings()
