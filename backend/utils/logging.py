import logging
import json
from datetime import datetime, timezone
from contextvars import ContextVar

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "request_id": request_id_context.get(),
                "customer_id": getattr(record, "customer_id", None),
                "conversation_id": getattr(record, "conversation_id", None),
                "whatsapp_message_id": getattr(record, "whatsapp_message_id", None),
                "duration_ms": getattr(record, "whatsapp_duration_ms", None),
                "message": record.getMessage(),
            },
            ensure_ascii=False,
        )


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
