"""Invariant 1 tests: at most one in_progress task per user.

Covers both interception paths of SingleActiveTaskGuard — activating a
brand-new insert and updating an existing row to in_progress — plus
per-user isolation and the InvariantLog audit trail.
"""

from sqlalchemy.orm import Session
from tests.helpers import active_tasks, make_task

from app.models import InvariantLog, Task, TaskStatus, User
from app.services.state import SingleActiveTaskGuard


def test_second_activation_demotes_first_to_queued(db: Session, user: User):
    guard = SingleActiveTaskGuard()
    first = make_task(user.id, "First")
    db.add(first)
    assert guard.activate_task(db, first) == []
    db.commit()

    second = make_task(user.id, "Second")
    db.add(second)
    demoted = guard.activate_task(db, second)
    db.commit()

    assert [t.id for t in demoted] == [first.id]
    assert db.get(Task, first.id).status == TaskStatus.QUEUED
    assert db.get(Task, second.id).status == TaskStatus.IN_PROGRESS
    assert [t.id for t in active_tasks(db, user.id)] == [second.id]


def test_update_to_in_progress_demotes_current_active(db: Session, user: User):
    guard = SingleActiveTaskGuard()
    current = make_task(user.id, "Current")
    db.add(current)
    guard.activate_task(db, current)

    challenger = make_task(user.id, "Challenger")  # plain queued insert
    db.add(challenger)
    db.commit()
    assert db.get(Task, challenger.id).status == TaskStatus.QUEUED

    demoted = guard.set_status(db, challenger, TaskStatus.IN_PROGRESS)
    db.commit()

    assert [t.id for t in demoted] == [current.id]
    assert db.get(Task, current.id).status == TaskStatus.QUEUED
    assert db.get(Task, challenger.id).status == TaskStatus.IN_PROGRESS
    assert [t.id for t in active_tasks(db, user.id)] == [challenger.id]


def test_guard_is_per_user(db: Session, user: User):
    other = User(phone_number="+15550002222")
    db.add(other)
    db.commit()

    guard = SingleActiveTaskGuard()
    mine = make_task(user.id, "Mine")
    theirs = make_task(other.id, "Theirs")
    db.add_all([mine, theirs])
    guard.activate_task(db, mine)
    guard.activate_task(db, theirs)
    db.commit()

    assert guard.get_active_task(db, user.id).id == mine.id
    assert guard.get_active_task(db, other.id).id == theirs.id


def test_demotion_is_logged(db: Session, user: User):
    guard = SingleActiveTaskGuard()
    first = make_task(user.id, "First")
    second = make_task(user.id, "Second")
    db.add_all([first, second])
    guard.activate_task(db, first)
    guard.activate_task(db, second)
    db.commit()

    logs = db.query(InvariantLog).filter_by(user_id=user.id).all()
    assert len(logs) == 1
    assert logs[0].invariant == "single_active_task"
    assert logs[0].action == "demote"
    assert str(first.id) in logs[0].detail


def test_reactivating_same_task_is_noop(db: Session, user: User):
    guard = SingleActiveTaskGuard()
    task = make_task(user.id, "Only")
    db.add(task)
    guard.activate_task(db, task)
    db.commit()

    assert guard.activate_task(db, task) == []
    db.commit()
    assert [t.id for t in active_tasks(db, user.id)] == [task.id]
    assert db.query(InvariantLog).filter_by(user_id=user.id).count() == 0


def test_completion_stamps_completed_at(db: Session, user: User):
    guard = SingleActiveTaskGuard()
    task = make_task(user.id, "Shippable")
    db.add(task)
    guard.activate_task(db, task)
    guard.set_status(db, task, TaskStatus.COMPLETED)
    db.commit()

    assert db.get(Task, task.id).completed_at is not None
