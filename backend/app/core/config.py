from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-secret-cambiar-en-cada-entorno-0123456789abcdef0123456789abcdef"  # noqa: S105
DEFAULT_EMERGENCY_MESSAGE = (
    "Si se trata de una emergencia, acuda de inmediato al servicio de Emergencia del "
    "Centro Médico San Bernardino o llame a los servicios de emergencia. "
    "Un agente revisará su mensaje con prioridad."
)


def _normalize_db_url(url: str) -> str:
    # Neon/Vercel entregan postgres:// o postgresql://; SQLAlchemy necesita el driver explícito.
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+psycopg://app:app@localhost:5432/atencion"
    database_url_unpooled: str | None = None

    jwt_secret: str = DEV_JWT_SECRET
    jwt_expire_minutes: int = 720
    session_cookie_name: str = "session"

    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_graph_version: str = "v23.0"
    whatsapp_force_dry_run: bool = False

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    cron_secret: str = ""
    timezone: str = "America/Caracas"

    # Reglas de negocio (pendientes de confirmar con el centro, §16)
    reopen_window_hours: int = 48
    abandon_after_hours: int = 24
    survey_cooldown_days: int = 30
    emergency_message: str = DEFAULT_EMERGENCY_MESSAGE
    bot_max_invalid_attempts: int = 3

    @field_validator("database_url", "database_url_unpooled")
    @classmethod
    def _normalize(cls, v: str | None) -> str | None:
        return _normalize_db_url(v) if v else v

    @model_validator(mode="after")
    def _require_real_secret(self) -> "Settings":
        if self.environment in ("preview", "production") and (
            self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 64
        ):
            raise ValueError("JWT_SECRET debe tener 64+ caracteres en preview y producción")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def whatsapp_dry_run(self) -> bool:
        """Sin credenciales (o forzado) no se llama a Meta: los envíos quedan SIMULATED."""
        return (
            self.whatsapp_force_dry_run
            or not self.whatsapp_access_token
            or not self.whatsapp_phone_number_id
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
