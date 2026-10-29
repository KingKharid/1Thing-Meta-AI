"""Focus & telemetry API tests: surface payloads, exactly-once completion."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from tests.helpers import make_task

import app.routers.focus as focus_router
from app.main import app
from app.models import Base, Task, TaskStatus, get_db
from app.services.state import SingleActiveTaskGuard

PHONE = "+15550001111"
HEADERS = {"X-Phone-Number": PHONE}


@pytest.fixture(autouse=True)
def no_provider_calls(monkeypatch):
    """The suite must never reach Meta or Baseten.

    Default is the honest failure branch: the model returns nothing, so
    title-only creation keeps the title and leaves the step empty, while
    a dump with nothing extractable at all answers 503. Tests that care
    about the derived path override this.
    """
    monkeypatch.setattr(focus_router, "triage", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        focus_router, "extract_or_fallback", lambda *args, **kwargs: ([], True)
    )


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


def test_create_task_requires_identity(client: TestClient):
    res = client.post("/api/v1/tasks", json={"title": "Nope"})
    assert res.status_code == 401


def test_create_task_activates_when_idle(client: TestClient):
    res = client.post(
        "/api/v1/tasks",
        headers=HEADERS,
        json={
            "title": "  Filed from the dock  ",
            "first_micro_step": "Open the thing",
            "estimated_minutes": 20,
            "energy_required": "high",
        },
    )

    assert res.status_code == 201
    body = res.json()
    assert body["activated"] is True
    assert body["task"]["title"] == "Filed from the dock"  # stripped
    assert body["task"]["energy_required"] == "high"
    assert body["active_task"]["id"] == body["task"]["id"]
    assert body["queued_backlog_count"] == 0

    focus = client.get("/api/v1/focus", headers=HEADERS).json()
    assert focus["selected_task"]["title"] == "Filed from the dock"


def test_create_task_queues_behind_active(client: TestClient):
    seed_active_with_reserve(client, reserve=1)

    res = client.post(
        "/api/v1/tasks",
        headers=HEADERS,
        json={"title": "New arrival"},
    )

    assert res.status_code == 201
    body = res.json()
    assert body["activated"] is False
    assert body["active_task"]["title"] == "Active work"
    assert body["queued_backlog_count"] == 2  # reserve incremented

    db = client.testing_session()
    try:
        created = db.get(Task, body["task"]["id"])
        assert created.status == TaskStatus.QUEUED
        assert created.estimated_minutes == 15  # schema default
        assert created.energy_required == "medium"  # schema default
    finally:
        db.close()


def test_create_without_step_asks_the_model(client: TestClient, monkeypatch):
    """A bare dump is decomposed by the model, not stored raw."""
    monkeypatch.setattr(
        focus_router,
        "triage",
        lambda *args, **kwargs: {
            "title": "Go to church",
            "first_micro_step": "Put on shoes and grab keys, wallet, phone",
            "estimated_minutes": 20,
            "energy_required": "low",
        },
    )

    res = client.post(
        "/api/v1/tasks", headers=HEADERS, json={"title": "going to church"}
    )

    assert res.status_code == 201
    body = res.json()
    assert body["step_source"] == "engine"
    assert body["task"]["title"] == "Go to church"
    assert body["task"]["first_micro_step"] == "Put on shoes and grab keys, wallet, phone"
    assert body["task"]["estimated_minutes"] == 20
    assert body["task"]["energy_required"] == "low"


def test_create_without_step_never_invents_one(client: TestClient):
    """Model down: the dump is kept, the step stays empty and says so."""
    res = client.post(
        "/api/v1/tasks", headers=HEADERS, json={"title": "going to church"}
    )

    assert res.status_code == 201
    body = res.json()
    assert body["step_source"] == "none"
    assert body["task"]["first_micro_step"] == ""
    assert body["task"]["title"] == "going to church"

    focus = client.get("/api/v1/focus", headers=HEADERS).json()
    assert focus["selected_task"]["first_micro_step"] == ""


def test_typed_step_skips_the_model(client: TestClient, monkeypatch):
    """The person already decomposed it; no provider call, no override."""
    calls: list[tuple] = []

    def fail(*args, **kwargs):
        calls.append(args)
        raise AssertionError("triage must not run when a step is typed")

    monkeypatch.setattr(focus_router, "triage", fail)

    res = client.post(
        "/api/v1/tasks",
        headers=HEADERS,
        json={"title": "Draft the update", "first_micro_step": "Open the doc"},
    )

    assert res.status_code == 201
    body = res.json()
    assert body["step_source"] == "user"
    assert body["task"]["first_micro_step"] == "Open the doc"
    assert calls == []


def test_derive_fills_a_missing_step(client: TestClient, monkeypatch):
    created = client.post(
        "/api/v1/tasks", headers=HEADERS, json={"title": "going to church"}
    ).json()
    task_id = created["task"]["id"]

    monkeypatch.setattr(
        focus_router,
        "triage",
        lambda *args, **kwargs: {
            "title": "Go to church",
            "first_micro_step": "Put on shoes and grab keys",
            "estimated_minutes": 20,
            "energy_required": "medium",
        },
    )

    res = client.post(f"/api/v1/tasks/{task_id}/derive", headers=HEADERS)

    assert res.status_code == 200
    body = res.json()
    assert body["first_micro_step"] == "Put on shoes and grab keys"
    assert body["title"] == "Go to church"


def test_derive_reports_failure_honestly(client: TestClient):
    created = client.post(
        "/api/v1/tasks", headers=HEADERS, json={"title": "going to church"}
    ).json()

    res = client.post(
        f"/api/v1/tasks/{created['task']['id']}/derive", headers=HEADERS
    )

    assert res.status_code == 503
    focus = client.get("/api/v1/focus", headers=HEADERS).json()
    assert focus["selected_task"]["first_micro_step"] == ""


def test_derive_unknown_task_is_404(client: TestClient):
    assert (
        client.post("/api/v1/tasks/999/derive", headers=HEADERS).status_code == 404
    )


def test_create_task_validation(client: TestClient):
    assert client.post("/api/v1/tasks", headers=HEADERS, json={}).status_code == 422
    assert (
        client.post(
            "/api/v1/tasks", headers=HEADERS, json={"title": "   "}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/tasks",
            headers=HEADERS,
            json={"title": "x", "energy_required": "cosmic"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/tasks",
            headers=HEADERS,
            json={"title": "x", "estimated_minutes": 0},
        ).status_code
        == 422
    )


def test_dump_files_every_task_and_activates_only_the_first(
    client: TestClient, monkeypatch
):
    """A week of thoughts: everything stored, exactly one thing shown."""
    extracted = [
        {
            "title": f"Task {i}",
            "first_micro_step": f"Start step {i}",
            "estimated_minutes": 10,
            "energy_required": "low",
        }
        for i in range(5)
    ]
    monkeypatch.setattr(focus_router, "extract_or_fallback", lambda *a, **k: (extracted, False))

    res = client.post(
        "/api/v1/tasks",
        headers=HEADERS,
        json={"dump": "a whole week of loose ends, in one message"},
    )

    assert res.status_code == 201
    body = res.json()
    assert body["filed_count"] == 5
    assert body["stashed_count"] == 4
    assert body["step_source"] == "engine"
    assert body["activated"] is True
    assert body["task"]["title"] == "Task 0"
    assert body["active_task"]["title"] == "Task 0"
    assert body["queued_backlog_count"] == 4

    db = client.testing_session()
    try:
        rows = db.query(Task).order_by(Task.id).all()
        assert [r.title for r in rows] == [f"Task {i}" for i in range(5)]
        active = [r for r in rows if r.status == TaskStatus.IN_PROGRESS]
        assert len(active) == 1
        assert active[0].title == "Task 0"
    finally:
        db.close()

    # The reserve count is exposed; reserve titles never are.
    focus = client.get("/api/v1/focus", headers=HEADERS).json()
    assert focus["selected_task"]["title"] == "Task 0"
    assert focus["queued_backlog_count"] == 4
    assert "Task 1" not in str(focus)


def test_dump_failure_files_nothing_and_says_so(client: TestClient):
    """A half-read week would silently lose work, so nothing is written."""
    res = client.post(
        "/api/v1/tasks",
        headers=HEADERS,
        json={"dump": "a whole week of loose ends"},
    )

    assert res.status_code == 503
    db = client.testing_session()
    try:
        assert db.query(Task).count() == 0
    finally:
        db.close()


def test_dump_never_yanks_the_task_in_focus(client: TestClient, monkeypatch):
    active = seed_active_with_reserve(client, reserve=0)
    monkeypatch.setattr(
        focus_router,
        "extract_or_fallback",
        lambda *a, **k: (
            [
                {
                    "title": "Something new",
                    "first_micro_step": "Open the laptop",
                    "estimated_minutes": 10,
                    "energy_required": "low",
                }
            ],
            False,
        ),
    )

    body = client.post(
        "/api/v1/tasks", headers=HEADERS, json={"dump": "something new"}
    ).json()

    assert body["activated"] is False
    assert body["active_task"]["id"] == active.id
    assert body["queued_backlog_count"] == 1


def test_dump_length_is_capped(client: TestClient):
    res = client.post(
        "/api/v1/tasks", headers=HEADERS, json={"dump": "x" * 8001}
    )
    assert res.status_code == 422


def test_dump_accepts_a_long_message(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        focus_router,
        "extract_or_fallback",
        lambda *a, **k: (
            [
                {
                    "title": "One thing",
                    "first_micro_step": "Open the doc",
                    "estimated_minutes": 10,
                    "energy_required": "low",
                }
            ],
            False,
        ),
    )
    res = client.post(
        "/api/v1/tasks", headers=HEADERS, json={"dump": "x" * 8000}
    )
    assert res.status_code == 201


def test_typed_step_wins_over_a_dump_without_dropping_it(
    client: TestClient, monkeypatch
):
    """A typed step applies to the head; the rest of the dump still files."""
    monkeypatch.setattr(
        focus_router,
        "extract_or_fallback",
        lambda *a, **k: (
            [
                {
                    "title": "Draft the update",
                    "first_micro_step": "Model's guess",
                    "estimated_minutes": 10,
                    "energy_required": "low",
                },
                {
                    "title": "other things",
                    "first_micro_step": "Read the pile",
                    "estimated_minutes": 5,
                    "energy_required": "low",
                },
            ],
            False,
        ),
    )

    res = client.post(
        "/api/v1/tasks",
        headers=HEADERS,
        json={
            "title": "Draft the update",
            "dump": "also a pile of other things",
            "first_micro_step": "Open the doc",
        },
    )

    assert res.status_code == 201
    body = res.json()
    assert body["step_source"] == "user"
    assert body["filed_count"] == 2
    assert body["task"]["title"] == "Draft the update"
    assert body["task"]["first_micro_step"] == "Open the doc"

    db = client.testing_session()
    try:
        rows = db.query(Task).order_by(Task.id).all()
        assert [r.title for r in rows] == ["Draft the update", "other things"]
    finally:
        db.close()


def test_skip_final_task_settles_to_empty(client: TestClient):
    """Regression: skipping the last task must not re-activate it."""
    active = seed_active_with_reserve(client, reserve=0)

    res = client.post(f"/api/v1/tasks/{active.id}/skip", headers=HEADERS)

    assert res.status_code == 200
    body = res.json()
    assert body["next_task"] is None
    assert body["queued_backlog_count"] == 1  # skipped row parked, not active

    db = client.testing_session()
    try:
        assert db.get(Task, active.id).status == TaskStatus.QUEUED
    finally:
        db.close()

    focus = client.get("/api/v1/focus", headers=HEADERS).json()
    assert focus["selected_task"] is None
    assert focus["queued_backlog_count"] == 1


def test_dump_falls_back_to_verbatim_filing(client: TestClient, monkeypatch):
    """Providers down: the dump still files, in the user's own words."""
    from app.services import triage as triage_module

    def boom(*args, **kwargs):
        raise RuntimeError("all providers down")

    monkeypatch.setattr(triage_module, "evaluate_single_task_meta", boom)
    monkeypatch.setattr(triage_module, "evaluate_single_task_baseten", boom)
    monkeypatch.setattr(
        focus_router, "extract_or_fallback", triage_module.extract_or_fallback
    )

    res = client.post(
        "/api/v1/tasks",
        headers=HEADERS,
        json={"dump": "Call the dentist about the crown\n\nWater the balcony plants"},
    )

    assert res.status_code == 201
    body = res.json()
    assert body["step_source"] == "heuristic"
    assert body["filed_count"] == 2
    assert body["stashed_count"] == 1
    assert body["activated"] is True
    assert body["task"]["title"] == "Call the dentist about the crown"
    assert body["task"]["first_micro_step"] == "Call the dentist about the crown"
    assert body["queued_backlog_count"] == 1
