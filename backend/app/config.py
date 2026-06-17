from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database. Defaults to local SQLite; Railway sets DATABASE_URL to Postgres.
    database_url: str = "sqlite:///./ripe_fitness.db"

    # Auth. JWT secret signs login tokens — set a long random value in prod.
    jwt_secret: str = "dev-insecure-change-me"
    jwt_expiry_days: int = 30
    # Set false to disable open self-signup (admin-created accounts only).
    allow_registration: bool = True

    # Claude.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # CORS.
    cors_origins: str = "http://localhost:5173"

    # Auto-sync scheduler. Times are 08:00 / 14:00 / 20:00 in this timezone.
    auto_sync_enabled: bool = True
    scheduler_timezone: str = "Australia/Sydney"

    @property
    def sqlalchemy_url(self) -> str:
        """Normalize the DB URL so SQLAlchemy uses the psycopg3 driver on Postgres.

        Railway hands out URLs like 'postgresql://...'; SQLAlchemy 2.0 needs the
        explicit '+psycopg' driver to use psycopg3.
        """
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
