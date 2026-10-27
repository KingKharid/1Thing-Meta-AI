"""Focus & telemetry API tests: surface payloads, exactly-once completion."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from tests.helpers import make_task

from app.main import app
from app.models import Base, Task, TaskStatus, get_db
from app.services.state import SingleActiveTaskGuard

PHONE = "+15550001111"
HEADERS = {"X-Phone-Number": PHONE}


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


def seed_active_with_reserve(client: TestClient, reserve: int = 2) -> Task:
    """Create a user with one active task and ``reserve`` queued tasks."""
    db = client.testing_session()
    try:
        from app.models import get_or_create_user

        user = get_or_create_user(db, phone_number=PHONE)
        guard = SingleActiveTaskGuard()
        active = make_task(user.id, "Active work")
        db.add(active)
        guard.activate_task(db, active)
        for i in range(reserve):
            db.add(make_task(user.id, f"Reserve {i}"))
        db.commit()
        return db.get(Task, active.id)
    finally:
        db.close()


def test_focus_requires_identity(client: TestClient):
    res = client.get("/api/v1/focus")
    assert res.status_code == 401


def test_focus_returns_active_plus_reserve_count_only(client: TestClient):
    seed_active_with_reserve(client, reserve=3)

    res = client.get("/api/v1/focus", headers=HEADERS)

    assert res.status_code == 200
    body = res.json()
    assert body["selected_task"]["title"] == "Active work"
    assert body["selected_task"]["first_micro_step"] == "Open the document"
    assert body["queued_backlog_count"] == 3
    assert "Reserve 0" not in res.text  # Invariant 2: titles stay hidden


def test_focus_empty_for_new_user(client: TestClient):
    res = client.get("/api/v1/focus", headers=HEADERS)

    assert res.status_code == 200
    assert res.json() == {"selected_task": None, "queued_backlog_count": 0}


def test_complete_promotes_next_and_is_idempotent(client: TestClient):
    active = seed_active_with_reserve(client, reserve=2)

    first = client.post(f"/api/v1/tasks/{active.id}/complete", headers=HEADERS)
    assert first.status_code == 200
    body = first.json()
    assert body["already_completed"] is False
    assert body["task"]["title"] == "Active work"
    assert body["next_task"]["title"] == "Reserve 0"  # least-recently-touched
    assert body["queued_backlog_count"] == 1
    assert body["rhythm"]["time_of_day"] in ("morning", "afternoon", "evening", "night")

    replay = client.post(f"/api/v1/tasks/{active.id}/complete", headers=HEADERS)
    assert replay.status_code == 200
    replay_body = replay.json()
    assert replay_body["already_completed"] is True
    # No double promotion: the same next task is still active.
    assert replay_body["next_task"]["id"] == body["next_task"]["id"]
    assert replay_body["queued_backlog_count"] == 1


def test_complete_rejects_foreign_and_missing_tasks(client: TestClient):
    assert (
        client.post("/api/v1/tasks/999/complete", headers=HEADERS).status_code == 404
    )
    seed_active_with_reserve(client)
    other = client.post(
        "/api/v1/tasks/1/complete", headers={"X-Phone-Number": "+19998887777"}
    )
    assert other.status_code == 404


def test_skip_reserve_returns_to_hidden_queue(client: TestClient):
    active = seed_active_with_reserve(client, reserve=1)

    res = client.post(f"/api/v1/tasks/{active.id}/skip", headers=HEADERS)

    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "reserve"
    assert body["next_task"]["title"] == "Reserve 0"
    assert body["queued_backlog_count"] == 1  # skipped task rejoined the reserve


def test_skip_archive_removes_from_rotation(client: TestClient):
    active = seed_active_with_reserve(client, reserve=1)

    res = client.post(f"/api/v1/tasks/{active.id}/skip?mode=archive", headers=HEADERS)

    assert res.status_code == 200
    assert res.json()["queued_backlog_count"] == 0

    replay = client.post(
        f"/api/v1/tasks/{active.id}/skip?mode=archive", headers=HEADERS
    )
    assert replay.json()["already_archived"] is True


def test_skip_rejects_bad_mode_and_completed_tasks(client: TestClient):
    active = seed_active_with_reserve(client)
    assert (
        client.post(f"/api/v1/tasks/{active.id}/skip?mode=vaporize", headers=HEADERS)
    ).status_code == 422

    done = client.post(f"/api/v1/tasks/{active.id}/complete", headers=HEADERS)
    assert done.status_code == 200
    skipped = client.post(f"/api/v1/tasks/{active.id}/skip", headers=HEADERS)
    assert skipped.status_code == 400


def test_telemetry_serves_six_planes(client: TestClient):
    seed_active_with_reserve(client, reserve=2)

    res = client.get("/api/v1/telemetry")

    assert res.status_code == 200
    planes = {plane["id"]: plane for plane in res.json()["planes"]}
    assert set(planes) == {"fleet", "llmops", "state", "users", "billing", "security"}
    state_rows = {row["key"]: row["value"] for row in planes["state"]["rows"]}
    assert state_rows["ACTIVE_TASKS"] == "1"
    assert state_rows["QUEUED"] == "2"
    assert all(plane["rows"] for plane in planes.values())
