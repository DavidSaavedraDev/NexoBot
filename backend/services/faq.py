import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Business, BusinessFAQ


class FAQService:
    def __init__(self, db: Session | None = None):
        self.db = db

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text.casefold())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        return "".join(ch for ch in normalized if ch.isalnum() or ch.isspace())

    @classmethod
    def _match_keywords(cls, text: str, *keywords: str) -> bool:
        normalized = cls._normalize_text(text)
        return any(cls._normalize_text(keyword) in normalized for keyword in keywords)

    def build_response(self, business: Business, text: str) -> str:
        normalized = self._normalize_text(text)
        if self.db is not None:
            for faq in self.db.scalars(
                select(BusinessFAQ).where(BusinessFAQ.business_id == business.id).order_by(BusinessFAQ.id)
            ).all():
                keywords = [part.strip() for part in faq.trigger.casefold().split(",") if part.strip()]
                if not keywords:
                    continue
                if any(self._match_keywords(normalized, keyword) for keyword in keywords):
                    return faq.response
                if faq.trigger.casefold() == "precio" and self._match_keywords(normalized, "precio", "precios", "costo", "cuesta", "cuanto", "vale"):
                    return faq.response
                if faq.trigger.casefold() == "horario" and self._match_keywords(normalized, "horario", "hora", "abierto", "atienden"):
                    return faq.response
                if faq.trigger.casefold() == "ubicacion" and self._match_keywords(normalized, "ubicacion", "direccion", "donde", "estan"):
                    return faq.response
        if any(word in normalized for word in ("hola", "buenas", "hello")):
            return f"Bienvenido a {business.name}. ¿En qué te podemos ayudar?"
        if any(word in normalized for word in ("horario", "hora", "abierto")):
            return business.business_hours or "Atendemos de lunes a sábado, por favor contáctanos."
        if any(word in normalized for word in ("precio", "precios", "costo", "cuesta", "cuanto", "vale")):
            return business.pricing or "Consulta nuestros precios por WhatsApp."
        if any(word in normalized for word in ("ubicacion", "direccion", "donde")):
            return f"Estamos en {business.address or 'nuestra dirección'}{', ' + business.city if business.city else ''}."
        return business.faq_text or "Gracias por escribirnos. Un miembro del equipo te responderá pronto."
