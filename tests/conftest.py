import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("WHATSAPP_APP_SECRET", "test-app-secret")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "change-me")
os.environ.setdefault("WHATSAPP_ACCESS_TOKEN", "test-access-token")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "123456789")
os.environ.setdefault("WHATSAPP_API_VERSION", "v21.0")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database.base import Base
from backend.database.session import get_db
from backend.main import app


@pytest.fixture()
def api_key_headers() -> dict[str, str]:
    return {"X-API-Key": os.environ.get("ADMIN_API_KEY", "test-admin-key")}


@pytest.fixture()
def signed_webhook_request():
    def _sign(payload_dict: dict, app_secret: str | None = None) -> tuple[bytes, dict[str, str]]:
        secret = app_secret or os.environ.get("WHATSAPP_APP_SECRET", "test-app-secret")
        body = json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
        signature = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        headers = {"X-Hub-Signature-256": signature, "Content-Type": "application/json"}
        return body, headers

    return _sign


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.state.test_session_factory = session_factory
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
