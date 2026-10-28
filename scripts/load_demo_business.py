from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.database.session import SessionLocal
from backend.models import Business, BusinessFAQ


def main() -> None:
    with SessionLocal() as db:
        business = db.query(Business).filter(Business.is_active.is_(True)).first()
        if business is None:
            business = Business(
                name="Peluquería Bella Estilo",
                description="Peluquería y barbería para hombres y mujeres.",
                business_hours="Lunes a sábado de 8:00am a 6:00pm.",
                address="Carrera 10 #15-22.",
                city="Moniquirá",
                pricing="Corte hombre $20.000, corte mujer $35.000, barba $15.000.",
                faq_text="Bienvenido a Peluquería Bella Estilo.",
                is_active=True,
            )
            db.add(business)
            db.flush()
        else:
            business.name = "Peluquería Bella Estilo"
            business.description = "Peluquería y barbería para hombres y mujeres."
            business.business_hours = "Lunes a sábado de 8:00am a 6:00pm."
            business.address = "Carrera 10 #15-22."
            business.city = "Moniquirá"
            business.pricing = "Corte hombre $20.000, corte mujer $35.000, barba $15.000."
            business.faq_text = "Bienvenido a Peluquería Bella Estilo."
        db.query(BusinessFAQ).filter(BusinessFAQ.business_id == business.id).delete()
        faqs = [
            {
                "trigger": "hola",
                "response": "Bienvenido a Peluquería Bella Estilo. ¿En qué te podemos ayudar?",
            },
            {
                "trigger": "horario",
                "response": "Atendemos de lunes a sábado de 8:00am a 6:00pm.",
            },
            {
                "trigger": "precio",
                "response": "El corte para hombre cuesta $20.000, el corte para mujer $35.000 y la barba $15.000.",
            },
            {
                "trigger": "ubicacion",
                "response": "Estamos en Carrera 10 #15-22, Moniquirá.",
            },
            {
                "trigger": "cita",
                "response": "Puedes agendar tu cita directamente por WhatsApp. Te atenderemos con gusto.",
            },
        ]
        for item in faqs:
            db.add(BusinessFAQ(business_id=business.id, trigger=item["trigger"], response=item["response"]))
        db.commit()
        print(f"Negocio cargado: {business.name}")


if __name__ == "__main__":
    main()
