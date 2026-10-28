import sys
import traceback
import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config.settings import Settings, get_settings, require_admin_api_key
from backend.database.session import get_db
from backend.models import Conversation, Customer, Message
from backend.schemas.admin import (
    ConversationResponse,
    CustomerResponse,
    MessageResponse,
)
from backend.schemas.whatsapp import WhatsAppWebhookMessage
from backend.services.webhook import WebhookService
from backend.services.whatsapp import WhatsAppClient

router = APIRouter(prefix="/api", tags=["Administration"])


class DemoWhatsAppMessage(BaseModel):
    phone: str = Field(..., min_length=1)
    name: str | None = None
    message: str = Field(..., min_length=1)


def pagination(page: int, page_size: int) -> tuple[int, int]:
    return (page - 1) * page_size, page_size


@router.get("/customers", response_model=dict)
def list_customers(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api_key),
    settings: Settings = Depends(get_settings),
) -> dict:
    offset, limit = pagination(page, page_size)
    total = db.scalar(select(func.count()).select_from(Customer)) or 0
    items = db.scalars(select(Customer).order_by(Customer.id).offset(offset).limit(limit)).all()
    return {"items": [CustomerResponse.model_validate(item) for item in items], "page": page, "page_size": page_size, "total": total}


@router.get("/conversations", response_model=dict)
def list_conversations(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api_key),
    settings: Settings = Depends(get_settings),
) -> dict:
    offset, limit = pagination(page, page_size)
    total = db.scalar(select(func.count()).select_from(Conversation)) or 0
    items = db.scalars(select(Conversation).order_by(Conversation.id).offset(offset).limit(limit)).all()
    return {"items": [ConversationResponse.model_validate(item) for item in items], "page": page, "page_size": page_size, "total": total}


@router.get("/messages", response_model=dict)
def list_messages(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api_key),
    settings: Settings = Depends(get_settings),
) -> dict:
    offset, limit = pagination(page, page_size)
    total = db.scalar(select(func.count()).select_from(Message)) or 0
    items = db.scalars(select(Message).order_by(Message.id).offset(offset).limit(limit)).all()
    return {"items": [MessageResponse.model_validate(item) for item in items], "page": page, "page_size": page_size, "total": total}


@router.post("/demo/message")
def simulate_demo_message(
    payload: DemoWhatsAppMessage,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, bool | str]:
    try:
        message_id = f"demo-{uuid.uuid4().hex[:12]}"
        result = WebhookService(db, WhatsAppClient(settings)).process(
            WhatsAppWebhookMessage(
                message_id=message_id,
                from_phone=payload.phone,
                text=payload.message,
                contact_name=payload.name,
            ),
            send_response=False,
        )
        return {"processed": result.processed, "response": result.response}
    except Exception as error:
        red = "\033[91m"
        reset = "\033[0m"
        print(f"{red}Error en POST /api/demo/message: {error}{reset}", file=sys.stderr)
        print(f"{red}{traceback.format_exc()}{reset}", file=sys.stderr, end="")
        raise
