import hashlib
import hmac
import logging
from time import perf_counter
from typing import Any

import httpx

from backend.config.settings import Settings

logger = logging.getLogger(__name__)


class WhatsAppConfigurationError(RuntimeError):
    """Raised when WhatsApp is enabled without a complete configuration."""


class WhatsAppClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def base_url(self) -> str:
        return f"https://graph.facebook.com/{self.settings.whatsapp_api_version}"

    def _require_configuration(self) -> None:
        missing = self.settings.whatsapp_missing_configuration()
        if missing:
            raise WhatsAppConfigurationError(
                f"Faltan variables de WhatsApp: {', '.join(missing)}"
            )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }

    def build_message_payload(self, recipient: str, text: str) -> dict[str, Any]:
        return {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": text},
        }

    def verify_webhook_signature(self, payload: bytes, signature: str | None) -> bool:
        if not self.settings.whatsapp_app_secret:
            return False
        if not signature:
            return False
        expected = "sha256=" + hmac.new(
            self.settings.whatsapp_app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def send_text(
        self,
        recipient: str,
        text: str,
        *,
        customer_id: int | None = None,
        conversation_id: int | None = None,
    ) -> None:
        if not self.settings.whatsapp_enabled:
            logger.info("WhatsApp deshabilitado; mensaje no enviado")
            return
        self._require_configuration()
        url = f"{self.base_url}/{self.settings.whatsapp_phone_number_id}/messages"
        started = perf_counter()
        payload = self.build_message_payload(recipient, text)
        try:
            response = httpx.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception(
                "Error API Meta al enviar mensaje",
                extra={
                    "customer_id": customer_id,
                    "conversation_id": conversation_id,
                    "whatsapp_duration_ms": round((perf_counter() - started) * 1000, 2),
                },
            )
            raise
        logger.info(
            "Mensaje enviado por WhatsApp",
            extra={
                "customer_id": customer_id,
                "conversation_id": conversation_id,
                "whatsapp_duration_ms": round((perf_counter() - started) * 1000, 2),
            },
        )

    def diagnose(self) -> dict[str, Any]:
        missing = self.settings.whatsapp_missing_configuration()
        result: dict[str, Any] = {
            "enabled": self.settings.whatsapp_enabled,
            "configuration_valid": not missing,
            "missing_configuration": missing,
            "api_version": self.settings.whatsapp_api_version,
            "phone_number_id_configured": bool(self.settings.whatsapp_phone_number_id),
            "access_token_configured": bool(self.settings.whatsapp_access_token),
            "verify_token_configured": bool(self.settings.whatsapp_verify_token),
            "token_valid": None,
            "connection_status": "disabled" if not self.settings.whatsapp_enabled else "not_checked",
        }
        if not self.settings.whatsapp_enabled:
            return result
        if missing:
            result["connection_status"] = "invalid_configuration"
            return result

        started = perf_counter()
        try:
            response = httpx.get(
                f"{self.base_url}/{self.settings.whatsapp_phone_number_id}",
                headers=self._headers(),
                params={"fields": "id,display_phone_number,verified_name"},
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            result["token_valid"] = False
            result["connection_status"] = "unavailable"
            result["error"] = self._safe_api_error(error)
            logger.exception(
                "Error API Meta durante diagn?stico",
                extra={"whatsapp_duration_ms": round((perf_counter() - started) * 1000, 2)},
            )
            return result
        result["token_valid"] = True
        result["connection_status"] = "connected"
        result["response_time_ms"] = round((perf_counter() - started) * 1000, 2)
        return result

    @staticmethod
    def _safe_api_error(error: httpx.HTTPError) -> str:
        if isinstance(error, httpx.HTTPStatusError):
            return f"Meta respondi? HTTP {error.response.status_code}"
        return "No se pudo conectar con Meta"
