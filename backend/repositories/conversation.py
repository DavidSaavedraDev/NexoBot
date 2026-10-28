from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Conversation, Customer, Message, MessageDirection


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_customer(self, business_id: int, phone: str, name: str | None) -> Customer:
        customer = self.db.scalar(
            select(Customer).where(Customer.business_id == business_id, Customer.phone == phone)
        )
        if customer is None:
            customer = Customer(business_id=business_id, phone=phone, name=name)
            self.db.add(customer)
            self.db.flush()
        elif name and customer.name != name:
            customer.name = name
        return customer

    def get_message_by_whatsapp_id(self, whatsapp_message_id: str) -> Message | None:
        return self.db.scalar(select(Message).where(Message.whatsapp_message_id == whatsapp_message_id))

    def record_message(
        self,
        business_id: int,
        phone: str,
        content: str,
        direction: MessageDirection,
        whatsapp_message_id: str | None = None,
        name: str | None = None,
    ) -> Message:
        if whatsapp_message_id:
            existing = self.get_message_by_whatsapp_id(whatsapp_message_id)
            if existing is not None:
                return existing
        customer = self.get_or_create_customer(business_id, phone, name)
        conversation = self.db.scalar(
            select(Conversation)
            .where(Conversation.business_id == business_id, Conversation.customer_id == customer.id)
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
        if conversation is None:
            conversation = Conversation(business_id=business_id, customer_id=customer.id)
            self.db.add(conversation)
            self.db.flush()
        message = Message(
            conversation_id=conversation.id,
            whatsapp_message_id=whatsapp_message_id,
            direction=direction,
            content=content,
        )
        self.db.add(message)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            if whatsapp_message_id:
                existing = self.get_message_by_whatsapp_id(whatsapp_message_id)
                if existing is not None:
                    return existing
            raise
        self.db.refresh(message)
        return message
