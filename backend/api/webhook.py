import json
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.config.settings import Settings, get_settings
from backend.database.session import get_db
from backend.schemas.whatsapp import WhatsAppWebhookResult, parse_cloud_messages
from backend.services.whatsapp import WhatsAppClient
from backend.services.webhook import WebhookService

router = APIRouter(prefix="/webhook", tags=["WhatsApp"])
logger = logging.getLogger(__name__)


@router.get("")
def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    if hub_mode != "subscribe" or hub_verify_token != settings.whatsapp_verify_token:
        raise HTTPException(status_code=403, detail="Token de verificación inválido")
    return PlainTextResponse(hub_challenge)


@router.post("", response_model=WhatsAppWebhookResult)
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WhatsAppWebhookResult:
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if settings.webhook_signature_is_configured():
        client = WhatsAppClient(settings)
        if not client.verify_webhook_signature(body, signature):
            logger.warning(
                "Webhook rechazado por firma inválida",
                extra={"signature_present": bool(signature)},
            )
            raise HTTPException(status_code=403, detail="Firma de webhook inválida")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Payload inválido") from None
    try:
        messages = parse_cloud_messages(payload)
        if not messages:
            return WhatsAppWebhookResult(processed=False, message_id="", response="Evento ignorado")
        result = WhatsAppWebhookResult(processed=False, message_id="", response="")
        service = WebhookService(db, WhatsAppClient(settings))
        for message in messages:
            logger.info(
                "Mensaje recibido desde WhatsApp",
                extra={"whatsapp_message_id": message.message_id},
            )
            result = service.process(message)
        return result
    except (httpx.HTTPError, RuntimeError, SQLAlchemyError):
        logger.exception("Error procesando mensaje de WhatsApp")
        raise HTTPException(status_code=502, detail="No se pudo procesar el mensaje") from None
