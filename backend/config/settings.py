import hmac
from functools import lru_cache

from fastapi import Depends, HTTPException, Request
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NexoBot"
    app_env: str = "development"
    database_url: str = "sqlite:///./nexobot.db"
    log_level: str = "INFO"
    whatsapp_verify_token: str = "change-me"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_api_version: str = "v21.0"
    whatsapp_enabled: bool = False
    whatsapp_app_secret: str = ""
    admin_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def whatsapp_missing_configuration(self) -> list[str]:
        required = {
            "WHATSAPP_ACCESS_TOKEN": self.whatsapp_access_token,
            "WHATSAPP_PHONE_NUMBER_ID": self.whatsapp_phone_number_id,
            "WHATSAPP_VERIFY_TOKEN": self.whatsapp_verify_token,
            "WHATSAPP_API_VERSION": self.whatsapp_api_version,
        }
        return [name for name, value in required.items() if not value.strip()]

    def whatsapp_configuration_is_valid(self) -> bool:
        return not self.whatsapp_missing_configuration()

    def webhook_signature_is_configured(self) -> bool:
        return bool(self.whatsapp_app_secret.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


def require_admin_api_key(request: Request, settings: Settings = Depends(get_settings)) -> None:
    provided = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    if not settings.admin_api_key:
        raise HTTPException(status_code=401, detail="API key no configurada")
    if not provided or not hmac.compare_digest(provided, settings.admin_api_key):
        raise HTTPException(status_code=401, detail="API key inv?lida")
