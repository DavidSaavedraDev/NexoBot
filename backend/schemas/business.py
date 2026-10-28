from pydantic import BaseModel, ConfigDict, Field


class FAQItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    trigger: str = Field(..., min_length=1)
    response: str = Field(..., min_length=1)


class BusinessConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    name: str = Field(..., min_length=1)
    description: str | None = None
    business_hours: str | None = None
    address: str | None = None
    city: str | None = None
    pricing: str | None = None
    faq_text: str | None = None
    is_active: bool = True
    faqs: list[FAQItem] = []
