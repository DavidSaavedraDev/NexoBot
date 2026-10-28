from sqlalchemy import select

from backend.models import Business, BusinessFAQ


def test_demo_business_is_loaded(client, api_key_headers):
    client.post(
        "/api/business",
        headers=api_key_headers,
        json={
            "name": "Peluquer?a Bella Estilo",
            "description": "Peluquer?a y barber?a para hombres y mujeres.",
            "business_hours": "Lunes a s?bado de 8:00am a 6:00pm.",
            "address": "Carrera 10 #15-22.",
            "city": "Moniquir?",
            "pricing": "Corte hombre $20.000, corte mujer $35.000, barba $15.000.",
            "faq_text": "Bienvenido a Peluquer?a Bella Estilo.",
            "faqs": [
                {"trigger": "hola", "response": "Bienvenido a Peluquer?a Bella Estilo."},
                {"trigger": "horario", "response": "Atendemos de lunes a s?bado de 8:00am a 6:00pm."},
                {"trigger": "precio", "response": "Corte hombre $20.000, corte mujer $35.000, barba $15.000."},
            ],
            "is_active": True,
        },
    )
    response = client.get("/api/business", headers=api_key_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Peluquer?a Bella Estilo"
    assert body["city"] == "Moniquir?"
    assert body["pricing"] == "Corte hombre $20.000, corte mujer $35.000, barba $15.000."


def test_faqs_are_customized_by_business(client, api_key_headers, signed_webhook_request):
    client.put(
        "/api/business",
        headers=api_key_headers,
        json={
            "name": "Peluquer?a Bella Estilo",
            "description": "Peluquer?a y barber?a.",
            "business_hours": "Lunes a s?bado de 8:00am a 6:00pm.",
            "address": "Carrera 10 #15-22.",
            "city": "Moniquir?",
            "pricing": "Corte hombre $20.000, corte mujer $35.000, barba $15.000.",
            "faq_text": "Bienvenido.",
            "is_active": True,
            "faqs": [
                {"trigger": "precio", "response": "El corte para hombre cuesta $20.000 y para mujer $35.000."},
                {"trigger": "horario", "response": "Atendemos de lunes a s?bado de 8:00am a 6:00pm."},
            ],
        },
    )
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "contacts": [{"wa_id": "5215551333333", "profile": {"name": "Cliente"}}],
                            "messages": [
                                {
                                    "from": "5215551333333",
                                    "id": "wamid-business-faq",
                                    "type": "text",
                                    "text": {"body": "?Cu?nto cuesta un corte?"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ]
            }
        ],
    }
    signed_body, signed_headers = signed_webhook_request(payload)
    response = client.post(
        "/webhook",
        content=signed_body,
        headers=signed_headers,
    )
    assert response.status_code == 200
    assert response.json()["response"] == "El corte para hombre cuesta $20.000 y para mujer $35.000."


def test_business_update_persists_changes(client, api_key_headers):
    payload = {
        "name": "Peluquer?a Bella Estilo",
        "description": "Barber?a y est?tica.",
        "business_hours": "Lunes a s?bado de 8:00am a 6:00pm.",
        "address": "Carrera 10 #15-22.",
        "city": "Moniquir?",
        "pricing": "Corte hombre $20.000, corte mujer $35.000, barba $15.000.",
        "faq_text": "Bienvenido a Peluquer?a Bella Estilo.",
        "is_active": True,
        "faqs": [{"trigger": "hola", "response": "Bienvenido a Peluquer?a Bella Estilo."}],
    }
    update = client.put("/api/business", headers=api_key_headers, json=payload)
    assert update.status_code == 200
    with client.app.state.test_session_factory() as session:
        business = session.scalar(select(Business))
        assert business.name == "Peluquer?a Bella Estilo"
        faq = session.scalar(select(BusinessFAQ))
        assert faq.response == "Bienvenido a Peluquer?a Bella Estilo."
