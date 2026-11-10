from functools import lru_cache
from typing import Literal
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    app_name: str = "InkaSec API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    frontend_origin: str = "http://localhost:5173"
    database_url: str = "sqlite:///./inkasec.db"
    jwt_secret_key: str
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_minutes: int = Field(default=30, ge=1, le=1440)
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    # Proxies de confianza delante de la API (p. ej. Render = 1). Con 0 se ignora
    # X-Forwarded-For, porque cualquier cliente puede inventar esa cabecera.
    trusted_proxy_hops: int = Field(default=0, ge=0, le=5)
    seed_demo_data: bool = False
    demo_password: str | None = None
    auto_create_tables: bool = True
    # RNF: la auditoría se conserva como mínimo 12 meses.
    audit_retention_days: int = Field(default=365, ge=365)
    arch_variant: str = "maximum"
    bootstrap_company_name: str = "InkaSec"
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_totp_secret: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @model_validator(mode="after")
    def _reject_insecure_config(self):
        if len(self.jwt_secret_key) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET_KEY debe tener al menos {MIN_JWT_SECRET_LENGTH} caracteres. "
                "Genera uno con: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        if self.frontend_origin.strip() == "*":
            raise ValueError("FRONTEND_ORIGIN no puede ser '*': la API envía cookies de sesión")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("COOKIE_SAMESITE=none exige COOKIE_SECURE=true")
        if self.is_production:
            if not self.cookie_secure:
                raise ValueError("En producción COOKIE_SECURE debe ser true (cookies solo por HTTPS)")
            if self.seed_demo_data:
                raise ValueError("En producción SEED_DEMO_DATA debe ser false (crearía cuentas demo)")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
