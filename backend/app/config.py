from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://medflow:medflow@localhost:5432/medflow"
    jwt_secret: str = "local-dev-only-change-me-use-setup-script"
    jwt_expire_minutes: int = 480
    jwt_algorithm: str = "HS256"
    cors_origins: str = "http://localhost:5173"
    storage_backend: str = "local"
    upload_dir: str = "uploads"
    seed_force: str = "0"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
