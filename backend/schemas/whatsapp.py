from typing import Any

from pydantic import BaseModel, Field


class WhatsAppWebhookMessage(BaseModel):
    message_id: str = Field(min_length=1)
    from_phone: str = Field(min_length=1)
    text: str = Field(min_length=1)
    contact_name: str | None = None


class WhatsAppWebhookResult(BaseModel):
    processed: bool
    message_id: str
    response: str


def parse_cloud_messages(payload: dict[str, Any]) -> list[WhatsAppWebhookMessage]:
    if "message_id" in payload:
        return [WhatsAppWebhookMessage.model_validate(payload)]

    messages: list[WhatsAppWebhookMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = value.get("contacts", [])
            names = {
                contact.get("wa_id"): contact.get("profile", {}).get("name")
                for contact in contacts
            }
            for message in value.get("messages", []):
                if message.get("type") != "text" or not message.get("text", {}).get("body"):
                    continue
                messages.append(
                    WhatsAppWebhookMessage(
                        message_id=message["id"],
                        from_phone=message["from"],
                        text=message["text"]["body"],
                        contact_name=names.get(message["from"]),
                    )
                )
    return messages
