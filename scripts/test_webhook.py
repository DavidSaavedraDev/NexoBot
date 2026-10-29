"""Envía un payload local con la misma estructura que WhatsApp Cloud API.

Uso:
    python scripts/test_webhook.py
    python scripts/test_webhook.py http://127.0.0.1:5000/webhook
"""

from __future__ import annotations

import sys

import requests


URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000/webhook"
PAYLOAD = {
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
                            "phone_number_id": "test-phone-number-id",
                        },
                        "contacts": [
                            {
                                "profile": {"name": "Prueba local"},
                                "wa_id": "5215551234567",
                            }
                        ],
                        "messages": [
                            {
                                "from": "5215551234567",
                                "id": "wamid.local-test-001",
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


response = requests.post(URL, json=PAYLOAD, timeout=10)
print(f"HTTP {response.status_code}")
print(response.text)
response.raise_for_status()
