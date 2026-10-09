from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="before")
    @classmethod
    def ignore_blank_values(cls, data: object) -> object:
        # A copied .env leaves keys blank. Those blanks must not override defaults
        # or fail integer parsing.
        if not isinstance(data, dict):
            return data
        return {
            key: value
            for key, value in data.items()
            if not (isinstance(value, str) and value.strip() == "")
        }

    database_url: str = "postgresql+psycopg://medflow:medflow@localhost:5432/medflow"
    jwt_secret: str = "secret"
    jwt_expire_minutes: int = 480
    jwt_algorithm: str = "HS256"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    storage_backend: str = "local"
    upload_dir: str = "uploads"
    seed_force: str = "0"
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_presign_seconds: int = 3600
    max_upload_bytes: int = 5 * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
