from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config.settings import require_admin_api_key
from backend.database.session import get_db
from backend.models import Business, BusinessFAQ
from backend.repositories.faq import FAQRepository
from backend.schemas.business import BusinessConfig, FAQItem

router = APIRouter(prefix="/api", tags=["Business"])


@router.get("/business", response_model=BusinessConfig)
def get_business(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api_key),
) -> BusinessConfig:
    business = db.scalar(select(Business).where(Business.is_active.is_(True)).limit(1))
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe un negocio configurado")
    repository = FAQRepository(db)
    items = repository.list_by_business(business.id)
    return BusinessConfig(
        id=business.id,
        name=business.name,
        description=business.description,
        business_hours=business.business_hours,
        address=business.address,
        city=business.city,
        pricing=business.pricing,
        faq_text=business.faq_text,
        is_active=business.is_active,
        faqs=[FAQItem(id=item.id, trigger=item.trigger, response=item.response) for item in items],
    )


@router.post("/business", response_model=BusinessConfig)
def create_business(
    request: Request,
    payload: BusinessConfig,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api_key),
) -> BusinessConfig:
    existing = db.scalar(select(Business).where(Business.is_active.is_(True)).limit(1))
    if existing is not None:
        return update_business(request, payload, db)
    business = Business(
        name=payload.name,
        description=payload.description,
        business_hours=payload.business_hours,
        address=payload.address,
        city=payload.city,
        pricing=payload.pricing,
        faq_text=payload.faq_text,
        is_active=True,
    )
    db.add(business)
    db.flush()
    repository = FAQRepository(db)
    repository.upsert_for_business(business.id, [item.model_dump() for item in payload.faqs])
    db.commit()
    db.refresh(business)
    return get_business(request, db)


@router.put("/business", response_model=BusinessConfig)
def update_business(
    request: Request,
    payload: BusinessConfig,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_api_key),
) -> BusinessConfig:
    business = db.scalar(select(Business).where(Business.is_active.is_(True)).limit(1))
    if business is None:
        return create_business(request, payload, db)
    business.name = payload.name
    business.description = payload.description
    business.business_hours = payload.business_hours
    business.address = payload.address
    business.city = payload.city
    business.pricing = payload.pricing
    business.faq_text = payload.faq_text
    business.is_active = payload.is_active
    repository = FAQRepository(db)
    repository.upsert_for_business(business.id, [item.model_dump() for item in payload.faqs])
    db.commit()
    db.refresh(business)
    return get_business(request, db)
