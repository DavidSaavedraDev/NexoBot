from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Business, BusinessFAQ


class FAQRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_business(self, business_id: int) -> list[BusinessFAQ]:
        return self.db.scalars(select(BusinessFAQ).where(BusinessFAQ.business_id == business_id).order_by(BusinessFAQ.id)).all()

    def upsert_for_business(self, business_id: int, polls: list[dict]) -> list[BusinessFAQ]:
        self.db.query(BusinessFAQ).filter(BusinessFAQ.business_id == business_id).delete()
        created: list[BusinessFAQ] = []
        for item in polls:
            faq = BusinessFAQ(
                business_id=business_id,
                trigger=item["trigger"],
                response=item["response"],
            )
            self.db.add(faq)
            created.append(faq)
        self.db.commit()
        return created


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
            business_hours="Lunes a viernes de 9:00 a 18:00",
            address="Calle principal 123",
            city="Moniquirá",
            pricing="Consulta por servicio",
        )
        self.db.add(business)
        self.db.commit()
        self.db.refresh(business)
        return business
