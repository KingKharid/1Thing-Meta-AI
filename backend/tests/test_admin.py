"""Admin surface tests: telemetry auth and the demo reset.

Both are public-facing in the sense that a judge touches them, so both
must fail closed and stay narrow.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models import Base, Task, TaskStatus, User, get_db
from app.services import auth

PHONE = "+15550001111"


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)
    client.testing_session = testing_session
    yield client
    app.dependency_overrides.clear()


def test_telemetry_requires_an_admin_key(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    assert client.get("/api/v1/telemetry").status_code == 401
    assert (
        client.get(
            "/api/v1/telemetry", headers={"X-Admin-Key": "wrong"}
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/telemetry", headers={"X-Admin-Key": "secret"}
        ).status_code
        == 200
    )


def test_telemetry_fails_closed_when_no_key_is_configured(client, monkeypatch):
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    res = client.get("/api/v1/telemetry", headers={"X-Admin-Key": "anything"})
    assert res.status_code == 503
    assert "not configured" in res.json()["detail"]


def test_admin_key_is_trimmed(monkeypatch):
    # A key pasted with trailing whitespace should still work.
    monkeypatch.setenv("ADMIN_API_KEY", "  spaced  ")
    assert auth.configured_admin_key() == "spaced"


def test_demo_reset_replaces_only_the_demo_identity(client, monkeypatch):
    monkeypatch.setenv("DEMO_PHONE", "+15550007777")

    db = client.testing_session()
    try:
        other = User(phone_number="+19998887777")
        db.add(other)
        db.flush()
        db.add(
            Task(
                user_id=other.id,
                title="Someone else's work",
                first_micro_step="Do not touch this",
                status=TaskStatus.IN_PROGRESS,
            )
        )
        db.commit()
    finally:
        db.close()

    res = client.post("/api/v1/demo/reset")
    assert res.status_code == 200
    body = res.json()
    assert body["phone"] == "+15550007777"
    assert body["task"]["title"] == "Lay out church outfit"
    assert body["task"]["first_micro_step"].startswith("Walk to closet")
    assert body["queued_backlog_count"] == 2

    db = client.testing_session()
    try:
        demo = db.query(User).filter_by(phone_number="+15550007777").one()
        demo_tasks = db.query(Task).filter_by(user_id=demo.id).all()
        assert len(demo_tasks) == 3
        assert demo_tasks[0].status == TaskStatus.IN_PROGRESS

        untouched = db.query(Task).filter_by(title="Someone else's work").one()
        assert untouched.status == TaskStatus.IN_PROGRESS
    finally:
        db.close()


def test_demo_reset_is_idempotent(client, monkeypatch):
    monkeypatch.setenv("DEMO_PHONE", "+15550007777")
    first = client.post("/api/v1/demo/reset")
    second = client.post("/api/v1/demo/reset")
    assert first.status_code == second.status_code == 200

    db = client.testing_session()
    try:
        demo = db.query(User).filter_by(phone_number="+15550007777").one()
        assert db.query(Task).filter_by(user_id=demo.id).count() == 3
    finally:
        db.close()
