"""Scheduler tests: midnight sweep (Invariant 4) and stall nudges (Invariant 5)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from tests.helpers import backdate, make_task

from app.models import InvariantLog, Task, TaskStatus, User
from app.services.scheduler import midnight_sweep, stall_nudge_check
from app.services.state import SingleActiveTaskGuard


def _activate(db: Session, task: Task) -> Task:
    db.add(task)
    SingleActiveTaskGuard().activate_task(db, task)
    db.commit()
    return task


def test_sweep_archives_completed_and_leaves_active_and_fresh_queued(
    db: Session, user: User
):
    done = _activate(db, make_task(user.id, "Done"))
    SingleActiveTaskGuard().set_status(db, done, TaskStatus.COMPLETED)
    active = _activate(db, make_task(user.id, "Active"))
    fresh = make_task(user.id, "Fresh reserve")
    db.add(fresh)
    db.commit()

    result = midnight_sweep(db)
    db.commit()

    assert result["archived_served"] == [done.id]
    assert result["archived_stale"] == []
    assert db.get(Task, done.id).status == TaskStatus.ARCHIVED
    assert db.get(Task, active.id).status == TaskStatus.IN_PROGRESS
    assert db.get(Task, fresh.id).status == TaskStatus.QUEUED


def test_sweep_archives_stale_queued_but_keeps_recent(db: Session, user: User):
    old = make_task(user.id, "Old reserve")
    recent = make_task(user.id, "Recent reserve")
    db.add_all([old, recent])
    db.commit()
    now = datetime.now(timezone.utc)
    backdate(db, old, updated_at=now - timedelta(days=8))
    backdate(db, recent, updated_at=now - timedelta(days=6))

    result = midnight_sweep(db, now=now)
    db.commit()

    assert result["archived_stale"] == [old.id]
    assert db.get(Task, old.id).status == TaskStatus.ARCHIVED
    assert db.get(Task, recent.id).status == TaskStatus.QUEUED


def test_nudge_fires_once_then_silence(db: Session, user: User):
    stalled = _activate(db, make_task(user.id, "Stalled"))
    now = datetime.now(timezone.utc)
    frozen = now - timedelta(minutes=200)
    backdate(db, stalled, updated_at=frozen)

    first = stall_nudge_check(db, now=now)
    db.commit()
    assert first == {"nudged": [stalled.id], "silenced": []}

    # Scheduler writes must not refresh the user-activity clock.
    assert db.get(Task, stalled.id).updated_at.replace(tzinfo=timezone.utc) == frozen

    # No second nudge while the episode is open.
    assert stall_nudge_check(db, now=now + timedelta(minutes=10)) == {
        "nudged": [],
        "silenced": [],
    }

    # 45 minutes after the nudge with no progress: total silence.
    silenced = stall_nudge_check(db, now=now + timedelta(minutes=46))
    db.commit()
    assert silenced == {"nudged": [], "silenced": [stalled.id]}
    assert db.get(Task, stalled.id).nudge_silenced is True

    # Silence holds on every later run.
    assert stall_nudge_check(db, now=now + timedelta(days=1)) == {
        "nudged": [],
        "silenced": [],
    }

    actions = [
        log.action
        for log in db.query(InvariantLog)
        .filter_by(user_id=user.id)
        .order_by(InvariantLog.id)
        .all()
    ]
    assert actions[-2:] == ["nudge", "nudge_silence"]


def test_fresh_active_task_is_not_nudged(db: Session, user: User):
    active = _activate(db, make_task(user.id, "Fresh"))
    backdate(db, active, updated_at=datetime.now(timezone.utc) - timedelta(minutes=30))

    assert stall_nudge_check(db) == {"nudged": [], "silenced": []}


def test_reactivation_opens_a_new_nudge_episode(db: Session, user: User):
    task = _activate(db, make_task(user.id, "Relapsed"))
    backdate(db, task, updated_at=datetime.now(timezone.utc) - timedelta(minutes=200))
    stall_nudge_check(db)
    db.commit()
    assert db.get(Task, task.id).last_nudged_at is not None

    SingleActiveTaskGuard().activate_task(db, db.get(Task, task.id))
    db.commit()

    refreshed = db.get(Task, task.id)
    assert refreshed.last_nudged_at is None
    assert refreshed.nudge_silenced is False
