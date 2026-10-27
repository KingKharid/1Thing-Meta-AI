"""Seed the local 1Thing SQLite database with a demo user + active task.

Run from the repository root:

    .\\.venv\\Scripts\\python seed_db.py        # Windows
    ./.venv/bin/python seed_db.py              # macOS / Linux

Creates ``backend/onething.db`` (the same file the API server uses when
started from ``backend/``), the demo user, and one active task. Safe to
re-run: existing rows are reused, never duplicated, and activation goes
through the single-active guard so Invariant 1 always holds.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

from app.models import (  # noqa: E402
    Base,
    SessionLocal,
    Task,
    TaskStatus,
    get_engine,
    get_or_create_user,
)
from app.services.state import SingleActiveTaskGuard  # noqa: E402

PHONE = "+15550007777"
DB_URL = f"sqlite:///{(ROOT / 'backend' / 'onething.db').as_posix()}"

TASK = {
    "title": "Review Hackathon Submission",
    "first_micro_step": "Check README and verify API endpoints",
    "estimated_minutes": 15,
    "energy_required": "high",
}


def main() -> None:
    engine = get_engine(DB_URL)
    SessionLocal.configure(bind=engine)
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        user = get_or_create_user(db, phone_number=PHONE)
        db.commit()

        guard = SingleActiveTaskGuard()
        active = guard.get_active_task(db, user.id)
        if active is not None and active.title == TASK["title"]:
            print(f"ALREADY SEEDED user_id={user.id} active_task_id={active.id}")
            return

        task = Task(user_id=user.id, status=TaskStatus.QUEUED, **TASK)
        db.add(task)
        demoted = guard.activate_task(db, task)
        db.commit()

        reserve = (
            db.query(Task)
            .filter(Task.user_id == user.id, Task.status == TaskStatus.QUEUED)
            .count()
        )
        print(
            f"SEEDED db=backend/onething.db user_id={user.id} phone={PHONE} "
            f"active_task_id={task.id} title={task.title!r} "
            f"reserve_count={reserve} demoted={[t.id for t in demoted]}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
