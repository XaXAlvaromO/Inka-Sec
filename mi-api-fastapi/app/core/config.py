from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "InkaSec API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    frontend_origin: str = "http://localhost:5173"
    database_url: str = "sqlite:///./inkasec.db"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    seed_demo_data: bool = False
    demo_password: str | None = None
    auto_create_tables: bool = True
    audit_retention_days: int = 365
    arch_variant: str = "maximum"
    bootstrap_company_name: str = "InkaSec"
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_totp_secret: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
