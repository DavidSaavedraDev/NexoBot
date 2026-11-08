"""Envía un payload local con la misma estructura que WhatsApp Cloud API.

Uso:
    python scripts/test_webhook.py
    python scripts/test_webhook.py http://127.0.0.1:5000/webhook 5215551234567

El remitente puede configurarse con WHATSAPP_TEST_SENDER. Si WHATSAPP_APP_SECRET
está definido, el script genera X-Hub-Signature-256 automáticamente.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import uuid

from dotenv import load_dotenv
import requests


def main() -> None:
    load_dotenv()
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000/webhook"
    sender = (
        sys.argv[2]
        if len(sys.argv) > 2
        else os.getenv("WHATSAPP_TEST_SENDER", "5215551234567")
    ).lstrip("+")
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "test-business-account",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000000",
                                "phone_number_id": os.getenv(
                                    "WHATSAPP_PHONE_NUMBER_ID", "test-phone-number-id"
                                ),
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Prueba local"},
                                    "wa_id": sender,
                                }
                            ],
                            "messages": [
                                {
                                    "from": sender,
                                    "id": f"wamid.local-{uuid.uuid4().hex}",
                                    "timestamp": "1761732000",
                                    "text": {"body": "Hola desde la prueba local"},
                                    "type": "text",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }
    raw_body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    headers = {"Content-Type": "application/json"}
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "").strip()
    if app_secret:
        digest = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        headers["X-Hub-Signature-256"] = f"sha256={digest}"

    print(f"POST {url}")
    print(f"Remitente: {sender}")
    response = requests.post(url, data=raw_body, headers=headers, timeout=10)
    print(f"HTTP {response.status_code}")
    print(response.text)
    response.raise_for_status()


if __name__ == "__main__":
    main()
