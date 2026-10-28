from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Business, Conversation, Customer, Message, MessageDirection


def seed_demo_data(db: Session) -> None:
    business = db.scalar(select(Business).where(Business.phone_number_id == "demo-phone"))
    if business is None:
        business = Business(
            name="NexoBot Demo",
            phone_number_id="demo-phone",
            description="Negocio de demostración",
            faq_text="Gracias por contactar a NexoBot Demo.",
        )
        db.add(business)
        db.flush()
    for index in range(1, 6):
        phone = f"52155510000{index}"
        customer = db.scalar(select(Customer).where(Customer.business_id == business.id, Customer.phone == phone))
        if customer is None:
            customer = Customer(business_id=business.id, phone=phone, name=f"Cliente Demo {index}")
            db.add(customer)
            db.flush()
        conversation = db.scalar(
            select(Conversation).where(
                Conversation.business_id == business.id, Conversation.customer_id == customer.id
            )
        )
        if conversation is None:
            conversation = Conversation(business_id=business.id, customer_id=customer.id)
            db.add(conversation)
            db.flush()
        if not db.scalar(select(Message).where(Message.conversation_id == conversation.id)):
            db.add_all(
                [
                    Message(
                        conversation_id=conversation.id,
                        direction=MessageDirection.INBOUND,
                        content="Hola, necesito información.",
                        whatsapp_message_id=f"demo-in-{index}",
                    ),
                    Message(
                        conversation_id=conversation.id,
                        direction=MessageDirection.OUTBOUND,
                        content="Hola, ¿en qué podemos ayudarte?",
                        whatsapp_message_id=f"demo-out-{index}",
                    ),
                ]
            )
    db.commit()
