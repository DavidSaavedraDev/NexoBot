"""Webhook Flask para mensajes de Meta (WhatsApp Cloud API e Instagram).

Variables de entorno relevantes:
    META_VERIFY_TOKEN o WHATSAPP_VERIFY_TOKEN: token configurado en Meta.
    DATABASE_URL: URL de SQLAlchemy, por ejemplo:
        sqlite:///./nexobot.db
        postgresql+psycopg://usuario:clave@localhost/nexobot
        mysql+pymysql://usuario:clave@localhost/nexobot

Para ejecutar localmente:
    python -m backend.main
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator

import requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request
from sqlalchemy import DateTime, String, Text, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


class Base(DeclarativeBase):
    """Base declarativa para la tabla de historial del webhook."""


class ReceivedMessage(Base):
    """Mensaje entrante normalizado, independientemente de su plataforma."""

    __tablename__ = "received_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[str] = mapped_column(String(255), index=True)
    content: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    external_message_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


@dataclass(frozen=True)
class IncomingMessage:
    """Representación común de un mensaje de WhatsApp o Instagram."""

    sender_id: str
    content: str
    platform: str
    external_message_id: str | None = None


def _database_url() -> str:
    """Obtiene la base configurada y deja SQLite como opción local segura."""
    return os.getenv("DATABASE_URL", "sqlite:///./nexobot.db")


def _create_database():
    url = _database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    Base.metadata.create_all(engine)
    return engine


engine = _create_database()
app = Flask(__name__)


def _verification_token() -> str:
    """Token temporal para pruebas locales."""
    return "mi_token_secreto_123"


def _valid_signature(raw_body: bytes) -> bool:
    """Valida X-Hub-Signature-256 cuando la validación no está desactivada."""
    if os.getenv("DISABLE_META_SIGNATURE_VALIDATION", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        logger.warning("Validación de firma Meta desactivada temporalmente")
        return True

    app_secret = os.getenv("META_APP_SECRET") or os.getenv("WHATSAPP_APP_SECRET")
    if not app_secret:
        return True

    supplied = request.headers.get("X-Hub-Signature-256", "")
    if not supplied.startswith("sha256="):
        return False
    expected = hmac.new(
        app_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(supplied.removeprefix("sha256="), expected)


def _text_message(
    sender_id: Any,
    text: Any,
    platform: str,
    message_id: Any = None,
) -> IncomingMessage | None:
    """Normaliza un mensaje de texto y descarta eventos sin texto."""
    if not isinstance(sender_id, (str, int)) or not isinstance(text, str):
        return None
    content = text.strip()
    if not content:
        return None
    return IncomingMessage(
        sender_id=str(sender_id),
        content=content,
        platform=platform,
        external_message_id=(
            str(message_id) if isinstance(message_id, (str, int)) else None
        ),
    )


def _parse_whatsapp(payload: dict[str, Any]) -> Iterator[IncomingMessage]:
    """Extrae messages[].text.body de entry[].changes[].value de WhatsApp."""
    for entry in payload.get("entry", []):
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes", []):
            if not isinstance(change, dict):
                continue
            value = change.get("value")
            if not isinstance(value, dict):
                continue
            for message in value.get("messages", []):
                if not isinstance(message, dict):
                    continue
                text = message.get("text")
                if not isinstance(text, dict):
                    continue
                parsed = _text_message(
                    message.get("from"),
                    text.get("body"),
                    "whatsapp",
                    message.get("id"),
                )
                if parsed:
                    yield parsed


def _parse_instagram(payload: dict[str, Any]) -> Iterator[IncomingMessage]:
    """Extrae messaging[].message.text de entry[] de Instagram."""
    for entry in payload.get("entry", []):
        if not isinstance(entry, dict):
            continue
        for event in entry.get("messaging", []):
            if not isinstance(event, dict):
                continue
            message = event.get("message")
            sender = event.get("sender")
            if not isinstance(message, dict) or not isinstance(sender, dict):
                continue
            parsed = _text_message(
                sender.get("id"),
                message.get("text"),
                "instagram",
                message.get("mid"),
            )
            if parsed:
                yield parsed


def parse_meta_messages(payload: dict[str, Any]) -> list[IncomingMessage]:
    """Identifica la plataforma y normaliza solo mensajes de texto."""
    if payload.get("object") == "whatsapp_business_account":
        return list(_parse_whatsapp(payload))
    if payload.get("object") == "instagram":
        return list(_parse_instagram(payload))
    return []


def save_message(message: IncomingMessage) -> bool:
    """Guarda un mensaje; los reintentos de Meta no crean duplicados."""
    with Session(engine) as db:
        try:
            if message.external_message_id:
                existing = db.scalar(
                    select(ReceivedMessage).where(
                        ReceivedMessage.external_message_id
                        == message.external_message_id
                    )
                )
                if existing:
                    return False
            db.add(
                ReceivedMessage(
                    sender_id=message.sender_id,
                    content=message.content,
                    platform=message.platform,
                    external_message_id=message.external_message_id,
                )
            )
            db.commit()
            return True
        except SQLAlchemyError:
            db.rollback()
            logger.exception("No se pudo persistir el mensaje entrante")
            return False


def process_bot_response(message: IncomingMessage) -> None:
    """Procesa el mensaje y envía una respuesta solo para WhatsApp.

    Los estados de entrega, mensajes sin texto y duplicados no llegan aquí.
    Instagram se guarda en el historial, pero requiere su propia API de
    respuestas y no debe enviarse accidentalmente mediante el endpoint de
    WhatsApp.
    """
    logger.info(
        "Mensaje de texto recibido",
        extra={
            "platform": message.platform,
            "sender_id": message.sender_id,
            "content": message.content,
        },
    )
    if message.platform == "whatsapp":
        send_whatsapp_text(
            recipient=message.sender_id,
            text=os.getenv(
                "WHATSAPP_REPLY_TEXT", "¡Hola! Recibí tu mensaje correctamente."
            ),
        )


def send_whatsapp_text(recipient: str, text: str) -> bool:
    """Envía un mensaje de texto por WhatsApp Cloud API.

    El token de acceso y el Phone Number ID se leen desde el entorno:
    ``WHATSAPP_ACCESS_TOKEN`` y ``WHATSAPP_PHONE_NUMBER_ID``.
    """
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    api_version = os.getenv("WHATSAPP_API_VERSION", "v21.0").strip()
    if not access_token or not phone_number_id:
        logger.error(
            "No se puede responder: faltan WHATSAPP_ACCESS_TOKEN "
            "o WHATSAPP_PHONE_NUMBER_ID"
        )
        return False

    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Error enviando respuesta por WhatsApp Cloud API")
        return False

    logger.info("Respuesta enviada por WhatsApp", extra={"recipient": recipient})
    return True


@app.get("/webhook")
def verify_webhook() -> Response:
    """Valida la suscripción de Meta y devuelve hub.challenge sin modificarlo."""
    mode = request.args.get("hub.mode", "")
    token = request.args.get("hub.verify_token", "")
    challenge = request.args.get("hub.challenge", "")
    expected_token = _verification_token()
    token_matches = hmac.compare_digest(token, expected_token)
    logger.info(
        "GET /webhook recibido: hub.mode=%r, hub.verify_token=%r, "
        "hub.challenge=%r, token_coincide=%s",
        mode,
        token,
        challenge,
        token_matches,
    )
    if (
        mode != "subscribe"
        or not expected_token
        or not token_matches
    ):
        logger.warning(
            "Verificación de /webhook rechazada: mode=%r, token_coincide=%s",
            mode,
            token_matches,
        )
        return Response("Forbidden", status=403, mimetype="text/plain")
    logger.info("Webhook verificado correctamente; devolviendo hub.challenge")
    return Response(challenge, status=200, mimetype="text/plain")


@app.post("/webhook")
def receive_webhook() -> Response:
    """Recibe eventos de Meta y siempre confirma rápidamente con 200."""
    try:
        raw_body = request.get_data(cache=True)
        logger.info(
            "POST /webhook recibido",
            extra={
                "content_type": request.content_type,
                "content_length": request.content_length,
                "signature_present": bool(
                    request.headers.get("X-Hub-Signature-256")
                ),
            },
        )
        if not _valid_signature(raw_body):
            logger.warning("Firma X-Hub-Signature-256 inválida")
            logger.info("POST /webhook rechazado por firma; devolviendo HTTP 200")
            return Response("EVENT_RECEIVED", status=200, mimetype="text/plain")

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            logger.warning(
                "Evento ignorado: JSON vacío o inválido",
                extra={"body_preview": raw_body[:500].decode("utf-8", "replace")},
            )
            logger.info("POST /webhook sin payload válido; devolviendo HTTP 200")
            return Response("EVENT_RECEIVED", status=200, mimetype="text/plain")

        logger.info(
            "Payload JSON recibido",
            extra={
                "object": payload.get("object"),
                "entry_count": len(payload.get("entry", []))
                if isinstance(payload.get("entry"), list)
                else 0,
            },
        )
        messages = parse_meta_messages(payload)
        logger.info("Mensajes de texto extraídos: %d", len(messages))
        for message in messages:
            logger.info(
                "Mensaje extraído de WhatsApp",
                extra={
                    "sender_id": message.sender_id,
                    "content": message.content,
                    "external_message_id": message.external_message_id,
                },
            )
            if save_message(message):
                process_bot_response(message)
            else:
                logger.info(
                    "Mensaje omitido: ya estaba persistido",
                    extra={"external_message_id": message.external_message_id},
                )
    except (SQLAlchemyError, TypeError, ValueError, KeyError):
        logger.exception("Error controlado procesando evento de Meta")
    except RuntimeError:
        logger.exception("Error de ejecución procesando evento de Meta")
    logger.info("POST /webhook procesado; devolviendo EVENT_RECEIVED con HTTP 200")
    return Response("EVENT_RECEIVED", status=200, mimetype="text/plain")


@app.get("/health")
def health() -> Response:
    """Endpoint mínimo para comprobar que el proceso está disponible."""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
