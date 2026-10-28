from fastapi import APIRouter, Depends, Request

from backend.config.settings import Settings, get_settings, require_admin_api_key
from backend.services.whatsapp import WhatsAppClient

router = APIRouter(prefix="/api/debug", tags=["Diagnostics"])


@router.get("/whatsapp")
def whatsapp_debug(
    request: Request,
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_admin_api_key),
) -> dict:
    configuration = WhatsAppClient(settings).diagnose()
    return {
        "service": "whatsapp_cloud_api",
        "status": configuration["connection_status"],
        "configuration": configuration,
    }
