import copy
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://app:app@localhost:5432/atencion_test"
)
os.environ.pop("DATABASE_URL_UNPOOLED", None)
os.environ["ENVIRONMENT"] = "test"
os.environ["WHATSAPP_APP_SECRET"] = "test-app-secret"
os.environ["WHATSAPP_VERIFY_TOKEN"] = "test-verify-token"
os.environ["WHATSAPP_FORCE_DRY_RUN"] = "true"
os.environ["CRON_SECRET"] = "test-cron-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_engine, get_sessionmaker  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Agent, Area, ContactReason  # noqa: E402
from app.models.enums import AgentRole  # noqa: E402
from app.seed import seed  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
PASSWORD = "clave-segura-123"


@pytest.fixture(scope="session", autouse=True)
def schema():
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def clean_db(schema):
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with get_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    with get_sessionmaker()() as db:
        seed(db, None, None)
    yield


@pytest.fixture
def db():
    with get_sessionmaker()() as session:
        yield session


def area_id(db, slug: str) -> int:
    return db.scalar(select(Area.id).where(Area.slug == slug))


def reason_id(db, name: str = "Información general") -> int:
    return db.scalar(select(ContactReason.id).where(ContactReason.name == name))


def make_agent(db, email: str, role: AgentRole = AgentRole.AGENT, area_slug: str | None = None):
    agent = Agent(
        name=email.split("@")[0].title(),
        email=email,
        password_hash=hash_password(PASSWORD),
        role=role,
        area_id=area_id(db, area_slug) if area_slug else None,
    )
    db.add(agent)
    db.commit()
    return agent


def login(email: str) -> TestClient:
    client = TestClient(app, base_url="https://testserver")
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def anon() -> TestClient:
    return TestClient(app, base_url="https://testserver")


@pytest.fixture
def supervisor(db) -> TestClient:
    make_agent(db, "supervisora@example.com", AgentRole.SUPERVISOR)
    return login("supervisora@example.com")


@pytest.fixture
def lab_agent(db) -> TestClient:
    make_agent(db, "lab@example.com", AgentRole.AGENT, "laboratorio")
    return login("lab@example.com")


@pytest.fixture
def general_agent(db) -> TestClient:
    make_agent(db, "general@example.com", AgentRole.AGENT, "atencion-paciente")
    return login("general@example.com")


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


_counter = {"n": 0}


def text_payload(body: str, wa_id: str = "584141234567", wamid: str | None = None) -> dict:
    payload = copy.deepcopy(load_fixture("text_message.json"))
    value = payload["entry"][0]["changes"][0]["value"]
    _counter["n"] += 1
    value["contacts"][0]["wa_id"] = wa_id
    message = value["messages"][0]
    message["from"] = wa_id
    message["id"] = wamid or f"wamid.test.{_counter['n']}"
    message["text"]["body"] = body
    return payload


def status_payload(wamid: str, status: str) -> dict:
    payload = copy.deepcopy(load_fixture("status_delivered.json"))
    entry = payload["entry"][0]["changes"][0]["value"]["statuses"][0]
    entry["id"] = wamid
    entry["status"] = status
    return payload


def sign(raw: bytes) -> str:
    digest = hmac.new(b"test-app-secret", raw, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def post_webhook(client: TestClient, payload: dict):
    raw = json.dumps(payload).encode()
    return client.post(
        "/api/webhooks/whatsapp",
        content=raw,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sign(raw)},
    )


def patient_says(client: TestClient, body: str, wa_id: str = "584141234567"):
    response = post_webhook(client, text_payload(body, wa_id))
    assert response.status_code == 200, response.text
    return response
