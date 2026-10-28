from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    phone: str
    name: str | None
    created_at: datetime | None
    updated_at: datetime | None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    customer_id: int
    started_at: datetime | None
    updated_at: datetime | None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    whatsapp_message_id: str | None
    direction: str
    content: str
    created_at: datetime | None


class PaginatedResponse(BaseModel):
    items: list[CustomerResponse | ConversationResponse | MessageResponse]
    page: int
    page_size: int
    total: int
