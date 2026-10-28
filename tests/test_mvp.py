import hashlib
import hmac
import json

from sqlalchemy import select

from backend.config.settings import Settings
from backend.models import Conversation, Customer, Message
from backend.services.whatsapp import WhatsAppClient, WhatsAppConfigurationError


def payload(message_id: str = "wamid-test-1") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "contacts": [{"wa_id": "5215550000000", "profile": {"name": "Ana"}}],
                            "messages": [
                                {
                                    "from": "5215550000000",
                                    "id": message_id,
                                    "type": "text",
                                    "text": {"body": "Hola"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ]
            }
        ],
    }


def signed_payload(payload_dict: dict, app_secret: str) -> tuple[bytes, str]:
    body = json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
    signature = "sha256=" + hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return body, signature


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_whatsapp_debug_does_not_expose_secrets(client, api_key_headers):
    response = client.get("/api/debug/whatsapp", headers=api_key_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "whatsapp_cloud_api"
    assert "access_token" not in body["configuration"]
    assert "verify_token" not in body["configuration"]


def test_enabled_whatsapp_fails_safely_without_credentials():
    settings = Settings(whatsapp_enabled=True, whatsapp_verify_token="")
    try:
        WhatsAppClient(settings).send_text("5215550000000", "test")
    except WhatsAppConfigurationError as error:
        assert "WHATSAPP_VERIFY_TOKEN" in str(error)
    else:
        raise AssertionError("Expected missing WhatsApp configuration to fail")


def test_whatsapp_client_builds_authorization_header():
    client = WhatsAppClient(Settings(whatsapp_access_token="abc123", whatsapp_phone_number_id="123456"))
    headers = client._headers()
    assert headers["Authorization"] == "Bearer abc123"
    assert headers["Content-Type"] == "application/json"


def test_whatsapp_client_builds_message_payload():
    payload_data = WhatsAppClient(Settings(whatsapp_access_token="abc123")).build_message_payload(
        "5215550000000", "Hola"
    )
    assert payload_data == {
        "messaging_product": "whatsapp",
        "to": "5215550000000",
        "type": "text",
        "text": {"body": "Hola"},
    }


def test_webhook_verification(client):
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "challenge",
            "hub.verify_token": "change-me",
        },
    )
    assert response.status_code == 200
    assert response.text == "challenge"


def test_webhook_rejects_invalid_signature(client):
    body = {"object": "whatsapp_business_account", "entry": []}
    response = client.post(
        "/webhook",
        json=body,
        headers={"X-Hub-Signature-256": "sha256=bad"},
    )
    assert response.status_code == 403


def test_webhook_accepts_valid_signature(client, signed_webhook_request):
    body = payload()
    signed_body, headers = signed_webhook_request(body)
    response = client.post(
        "/webhook",
        content=signed_body,
        headers=headers,
    )
    assert response.status_code == 200


def test_webhook_registers_customer_conversation_and_messages(client, signed_webhook_request):
    signed_body, headers = signed_webhook_request(payload())
    response = client.post(
        "/webhook",
        content=signed_body,
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["processed"] is True
    with client.app.state.test_session_factory() as session:
        assert session.scalar(select(Customer)) is not None
        assert session.scalar(select(Conversation)) is not None
        assert len(session.scalars(select(Message)).all()) == 2


def test_webhook_is_idempotent(client, signed_webhook_request):
    first_body, first_headers = signed_webhook_request(payload("wamid-duplicate"))
    second_body, second_headers = signed_webhook_request(payload("wamid-duplicate"))
    first = client.post(
        "/webhook",
        content=first_body,
        headers=first_headers,
    )
    second = client.post(
        "/webhook",
        content=second_body,
        headers=second_headers,
    )
    assert first.json()["processed"] is True
    assert second.json() == {"processed": False, "message_id": "wamid-duplicate", "response": ""}


def test_demo_message_endpoint_processes_local_message(client):
    response = client.post(
        "/api/demo/message",
        json={"phone": "573001112233", "name": "Carlos", "message": "hola"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["processed"] is True
    assert body["response"] == "Bienvenido a Mi negocio. ¿En qué te podemos ayudar?"


def test_admin_endpoints_require_api_key(client):
    assert client.get("/api/customers").status_code == 401
    assert client.get("/api/conversations").status_code == 401
    assert client.get("/api/messages").status_code == 401
    assert client.get("/api/business").status_code == 401
    assert client.get("/api/debug/whatsapp").status_code == 401


def test_admin_endpoints_are_paginated(client, api_key_headers, signed_webhook_request):
    signed_body, signed_headers = signed_webhook_request(payload("wamid-admin"))
    client.post(
        "/webhook",
        content=signed_body,
        headers=signed_headers,
    )
    response = client.get("/api/customers?page=1&page_size=1", headers=api_key_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1
    assert client.get("/api/conversations", headers=api_key_headers).json()["total"] == 1
    assert client.get("/api/messages", headers=api_key_headers).json()["total"] == 2
