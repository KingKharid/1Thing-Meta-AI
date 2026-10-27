"""Shared builders for backend tests."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Task


def make_task(user_id: int, title: str = "Do the thing", **overrides) -> Task:
    fields = {
        "user_id": user_id,
        "title": title,
        "first_micro_step": "Open the document",
        "estimated_minutes": 10,
        "energy_required": "low",
    }
    fields.update(overrides)
    return Task(**fields)


def backdate(db: Session, task: Task, **fields: datetime) -> Task:
    """Set timestamp columns directly, bypassing the ORM onupdate hook."""
    db.query(Task).filter_by(id=task.id).update(fields, synchronize_session=False)
    db.commit()
    return db.get(Task, task.id)


def active_tasks(db: Session, user_id: int) -> list[Task]:
    from app.models import TaskStatus

    return (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.status == TaskStatus.IN_PROGRESS)
        .all()
    )
