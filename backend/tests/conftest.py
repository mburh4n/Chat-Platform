"""Shared test setup.

Tests run against a separate database (pdfchat_test) on the same PostgreSQL
server as development, so real pgvector queries are exercised. Emails are
captured instead of sent. Nothing here touches the development database.
"""

import os
import re

# --- Point the app at the test database BEFORE anything else imports settings ---
from app.core import config

_TEST_DB_NAME = os.environ.get("TEST_DB_NAME", "pdfchat_test")
os.environ["DATABASE_URL"] = config.settings.database_url.rsplit("/", 1)[0] + f"/{_TEST_DB_NAME}"
config.get_settings.cache_clear()
config.settings = config.get_settings()

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.emails import service as email_service  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Build the schema once per test run with the real Alembic migrations."""
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    alembic_config = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    alembic_config.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    command.upgrade(alembic_config, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    """Every test starts with empty tables."""
    yield
    table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))


class Outbox:
    """Collects emails instead of sending them through Gmail."""

    def __init__(self) -> None:
        self.messages: list[dict] = []

    def last_code(self, to_email: str) -> str:
        for message in reversed(self.messages):
            if message["to_email"] == to_email:
                return re.search(r"\b(\d{6})\b", message["text_body"]).group(1)
        raise AssertionError(f"No email was sent to {to_email}")


@pytest.fixture(autouse=True)
def outbox(monkeypatch) -> Outbox:
    box = Outbox()

    def fake_send_email(to_email, subject, text_body, html_body=None):
        box.messages.append({"to_email": to_email, "subject": subject, "text_body": text_body})

    monkeypatch.setattr(email_service, "send_email", fake_send_email)
    return box


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


PASSWORD = "StrongPass123"


def register_and_login(client: TestClient, outbox: Outbox, email: str, name: str = "Test User") -> str:
    """Create a verified user and return an access token."""
    response = client.post("/api/auth/signup", json={"name": name, "email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    code = outbox.last_code(email)
    response = client.post("/api/auth/verify-email", json={"email": email, "otp": code})
    assert response.status_code == 200, response.text
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
