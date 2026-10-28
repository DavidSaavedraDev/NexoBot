from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Business


class BusinessRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active(self) -> Business | None:
        return self.db.scalar(select(Business).where(Business.is_active.is_(True)).limit(1))

    def get_or_create_default(self) -> Business:
        business = self.get_active()
        if business:
            return business
        business = Business(
            name="Mi negocio",
            description="Asistente virtual de NexoBot",
            faq_text="Hola, somos un negocio atendido por NexoBot.",
        )
        self.db.add(business)
        self.db.commit()
        self.db.refresh(business)
        return business
