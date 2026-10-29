"""Pipeline tests: the model writes the step, the surface never invents one.

``handle_pipeline`` owns the WhatsApp path. It used to build a fixed
``{25, medium, morning}`` context and to persist whatever the model sent.
Both are covered here, plus the failure branch that must not create a task
with a made-up step.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main
from app.models import Base, Task

PHONE = "+15550002222"

DERIVED = {
    "title": "Get ready for church",
    "first_micro_step": "Put on shoes and grab keys by the door",
    "estimated_minutes": 20,
    "energy_required": "low",
}


@pytest.fixture()
def pipeline(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(main, "SessionLocal", factory)

    sent: list[tuple[str, str, int | None]] = []
    monkeypatch.setattr(main, "_deliver", lambda uid, body: sent.append((uid, body, None)))
    monkeypatch.setattr(
        main,
        "_deliver_focus",
        lambda uid, body, task_id=None: sent.append((uid, body, task_id)),
    )

    return {"factory": factory, "sent": sent}


def test_pipeline_persists_the_derived_step(pipeline, monkeypatch):
    seen_context: list[dict] = []

    def fake_extract(raw_text, context, engine="meta", limit=20):
        seen_context.append(context)
        return [DERIVED], False

    monkeypatch.setattr(main, "extract_or_fallback", fake_extract)

    main.handle_pipeline("going to church", user_id=PHONE)

    db = pipeline["factory"]()
    try:
        task = db.query(Task).one()
        assert task.first_micro_step == "Put on shoes and grab keys by the door"
        assert task.title == "Get ready for church"
        assert task.estimated_minutes == 20
        assert task.energy_required == "low"
    finally:
        db.close()

    # Real rhythm, not the old hardcoded morning/medium/25.
    assert seen_context
    assert set(seen_context[0]) == {"available_minutes", "energy", "time_of_day"}


def test_pipeline_failure_sends_an_honest_reply(pipeline, monkeypatch):
    # Total extraction failure — AI down AND nothing heuristic to file.
    monkeypatch.setattr(main, "extract_or_fallback", lambda *args, **kwargs: ([], True))

    result = main.handle_pipeline("going to church", user_id=PHONE)

    assert result == {}
    db = pipeline["factory"]()
    try:
        assert db.query(Task).count() == 0
    finally:
        db.close()
    assert pipeline["sent"], "the user must not be left in silence"


def test_pipeline_sends_focus_reply_with_the_task_id(pipeline, monkeypatch):
    monkeypatch.setattr(main, "extract_or_fallback", lambda *args, **kwargs: ([DERIVED], False))

    main.handle_pipeline("going to church", user_id=PHONE)

    focus_calls = [entry for entry in pipeline["sent"] if entry[2] is not None]
    assert len(focus_calls) == 1
    assert focus_calls[0][2] > 0


def test_pipeline_queues_the_rest_of_a_dump(pipeline, monkeypatch):
    """A week of thoughts on WhatsApp: one on the surface, the rest hidden."""
    tasks = [
        {"title": f"Task {i}", "first_micro_step": f"Start step {i}",
         "estimated_minutes": 10, "energy_required": "low"}
        for i in range(4)
    ]
    monkeypatch.setattr(main, "extract_or_fallback", lambda *args, **kwargs: (tasks, False))

    result = main.handle_pipeline("a whole week of loose ends", user_id=PHONE)

    assert result["selected_task"]["title"] == "Task 0"
    assert result["filed_count"] == 4
    assert result["stashed_count"] == 3
    assert result["queued_backlog_count"] == 3

    db = pipeline["factory"]()
    try:
        from app.models import TaskStatus

        active = db.query(Task).filter(Task.status == TaskStatus.IN_PROGRESS).all()
        assert len(active) == 1
        assert active[0].title == "Task 0"
    finally:
        db.close()


def test_pipeline_falls_back_to_verbatim_filing(pipeline, monkeypatch):
    """Providers down: the user's own words still file, nothing invented."""
    from app.services import triage as triage_module

    def boom(*args, **kwargs):
        raise RuntimeError("all providers down")

    monkeypatch.setattr(triage_module, "evaluate_single_task_meta", boom)
    monkeypatch.setattr(triage_module, "evaluate_single_task_baseten", boom)

    result = main.handle_pipeline(
        "Call the dentist about the crown\n\nWater the balcony plants",
        user_id=PHONE,
    )

    assert result["filed_count"] == 2
    assert result["selected_task"]["title"] == "Call the dentist about the crown"
    assert result["queued_backlog_count"] == 1

    db = pipeline["factory"]()
    try:
        from app.models import TaskStatus

        rows = db.query(Task).order_by(Task.id).all()
        assert [t.title for t in rows] == [
            "Call the dentist about the crown",
            "Water the balcony plants",
        ]
        assert rows[0].status == TaskStatus.IN_PROGRESS
        assert rows[1].status == TaskStatus.QUEUED
        # Lossless: the full chunk survives as the step.
        assert rows[0].first_micro_step == "Call the dentist about the crown"
    finally:
        db.close()

    assert pipeline["sent"], "the user must still get the focus reply"
