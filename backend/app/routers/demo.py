"""One-click demo reset for judges.

The demo page is public, so this endpoint is deliberately narrow: it can
only touch the identity named by ``DEMO_PHONE`` and it never accepts a
phone number from the caller. A judge can press RESET as often as they
like without touching anyone else's work.

The seeded task is the same one the video opens on, so the first thing a
visitor sees is a real step — not an empty surface.
"""

from __future__ import annotations

import os

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.models import Task, TaskStatus, get_db, get_or_create_user
from app.services.ratelimit import rate_limit

router = APIRouter(
    prefix="/api/v1", tags=["demo"], dependencies=[Depends(rate_limit)]
)

DEMO_PHONE = os.getenv("DEMO_PHONE", "+15550007777")

SEED_TASK = {
    "title": "Lay out church outfit",
    "first_micro_step": (
        "Walk to closet and lay tomorrow's shirt, pants, and shoes on bed"
    ),
    "estimated_minutes": 15,
    "energy_required": "medium",
}

# Two queued tasks behind the seeded head, so DONE promotes instead of
# emptying the surface. A single seeded task teaches the judge that the
# product ends after one press — the opposite of the truth.
SEED_RESERVE = [
    {
        "title": "Send overdue venue deposit",
        "first_micro_step": (
            "Open email, search venue name, open invoice and click the "
            "payment link with card in hand"
        ),
        "estimated_minutes": 10,
        "energy_required": "medium",
    },
    {
        "title": "Call dentist about painful crown",
        "first_micro_step": (
            "Pick up phone, search contacts for dentist, tap call and read "
            "script: ask for the earliest check-up"
        ),
        "estimated_minutes": 10,
        "energy_required": "high",
    },
]


@router.post("/demo/reset")
def reset_demo(
    mode: Literal["task", "dump"] = Query(default="task"),
    db: Session = Depends(get_db),
):
    """Clear the demo identity and leave it in one of two honest states.

    - ``task``: one real active task with two queued behind it, so a
      visitor lands on a step and DONE promotes instead of emptying.
    - ``dump``: an empty surface, so the next dump is the thing that
      activates the head. Seeding a task here would make Invariant 1
      (never yank an in-progress task) hide the demo's whole point.
    """
    user = get_or_create_user(db, phone_number=DEMO_PHONE)
    db.query(Task).filter(Task.user_id == user.id).delete(synchronize_session=False)

    task = None
    queued = 0
    if mode == "task":
        task = Task(user_id=user.id, status=TaskStatus.IN_PROGRESS, **SEED_TASK)
        db.add(task)
        for seed in SEED_RESERVE:
            db.add(Task(user_id=user.id, status=TaskStatus.QUEUED, **seed))
        queued = len(SEED_RESERVE)
    db.commit()

    return {
        "phone": DEMO_PHONE,
        "mode": mode,
        "task": (
            {
                "id": task.id,
                "title": task.title,
                "first_micro_step": task.first_micro_step,
                "estimated_minutes": task.estimated_minutes,
                "energy_required": task.energy_required,
            }
            if task is not None
            else None
        ),
        "queued_backlog_count": queued,
    }
