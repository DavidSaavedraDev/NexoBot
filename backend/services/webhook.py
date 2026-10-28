import logging

from sqlalchemy.orm import Session

from backend.models import MessageDirection
from backend.repositories.business import BusinessRepository
from backend.repositories.conversation import ConversationRepository
from backend.schemas.whatsapp import WhatsAppWebhookMessage, WhatsAppWebhookResult
from backend.services.faq import FAQService
from backend.services.whatsapp import WhatsAppClient

logger = logging.getLogger(__name__)


class WebhookService:
    def __init__(self, db: Session, whatsapp: WhatsAppClient):
        self.db = db
        self.whatsapp = whatsapp

    def process(
        self,
        payload: WhatsAppWebhookMessage,
        *,
        send_response: bool = True,
    ) -> WhatsAppWebhookResult:
        business = BusinessRepository(self.db).get_or_create_default()
        repository = ConversationRepository(self.db)
        existing = repository.get_message_by_whatsapp_id(payload.message_id)
        if existing:
            return WhatsAppWebhookResult(
                processed=False, message_id=payload.message_id, response=""
            )
        repository.record_message(
            business_id=business.id,
            phone=payload.from_phone,
            content=payload.text,
            direction=MessageDirection.INBOUND,
            whatsapp_message_id=payload.message_id,
            name=payload.contact_name,
        )
        customer = repository.get_message_by_whatsapp_id(payload.message_id)
        customer_id = customer.conversation.customer_id if customer else None
        conversation_id = customer.conversation_id if customer else None
        logger.info(
            "Mensaje entrante registrado",
            extra={
                "customer_id": customer_id,
                "conversation_id": conversation_id,
            },
        )
        response_text = FAQService(self.db).build_response(business, payload.text)
        if send_response:
            self.whatsapp.send_text(
                payload.from_phone,
                response_text,
                customer_id=customer_id,
                conversation_id=conversation_id,
            )
        repository.record_message(
            business_id=business.id,
            phone=payload.from_phone,
            content=response_text,
            direction=MessageDirection.OUTBOUND,
        )
        return WhatsAppWebhookResult(processed=True, message_id=payload.message_id, response=response_text)
