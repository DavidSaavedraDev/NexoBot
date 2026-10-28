import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import Response

from backend.api.webhook import router as webhook_router
from backend.api.admin import router as admin_router
from backend.api.business import router as business_router
from backend.api.debug import router as debug_router
from backend.config.settings import get_settings
from backend.utils.logging import configure_logging
from backend.utils.logging import request_id_context


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(webhook_router)
app.include_router(admin_router)
app.include_router(business_router)
app.include_router(debug_router)


@app.middleware("http")
async def request_context(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_context.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_context.reset(token)


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
