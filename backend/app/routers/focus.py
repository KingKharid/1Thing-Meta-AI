"""Focus & task-action API.

- ``GET /api/v1/focus``: the single active task plus the hidden reserve
  *count* — never reserve titles (Invariant 2).
- ``POST /api/v1/tasks/{id}/complete``: exactly-once completion
  (Invariant 6). Idempotent across watch, phone, WhatsApp, and web:
  replays return the settled state without double effects, and the next
  queued task is surfaced.
- ``POST /api/v1/tasks/{id}/skip``: move a task out of rotation, either
  back to the hidden reserve (``mode=reserve``, default) or to the
  archive (``mode=archive``).

Identity (MVP): the ``X-Phone-Number`` header resolves the caller via
:func:`get_or_create_user`, matching the phone-OTP identity model
(Invariant 7). A session-middleware check replaces this seam when OTP
login lands.
"""

from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import Task, TaskStatus, get_db, get_or_create_user
from app.services.rhythm import suggest_context
from app.services.state import SingleActiveTaskGuard

router = APIRouter(prefix="/api/v1", tags=["focus"])

guard = SingleActiveTaskGuard()


class TaskOut(BaseModel):
    id: int
    title: str
    first_micro_step: str
    estimated_minutes: int
    energy_required: str


class FocusOut(BaseModel):
    selected_task: TaskOut | None
    queued_backlog_count: int


class RhythmOut(BaseModel):
    available_minutes: int
    energy: str
    time_of_day: str


class CompleteOut(BaseModel):
    task: TaskOut
    next_task: TaskOut | None
    queued_backlog_count: int
    already_completed: bool = False
    rhythm: RhythmOut


class SkipOut(BaseModel):
    task: TaskOut
    next_task: TaskOut | None
    queued_backlog_count: int
    already_archived: bool = False
    mode: str


def task_out(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        title=task.title,
        first_micro_step=task.first_micro_step,
        estimated_minutes=task.estimated_minutes,
        energy_required=task.energy_required,
    )


def get_current_user_id(
    db: Session = Depends(get_db),
    x_phone_number: str | None = Header(default=None),
) -> int:
    phone = (x_phone_number or "").strip()
    if not phone:
        raise HTTPException(status_code=401, detail="Missing X-Phone-Number identity header")
    user = get_or_create_user(db, phone_number=phone)
    db.commit()
    return user.id


def _reserve_count(db: Session, user_id: int) -> int:
    return (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.status == TaskStatus.QUEUED)
        .count()
    )


def _promote_next_queued(db: Session, user_id: int) -> Task | None:
    """Surface the least-recently-touched reserve task as active.

    Touch-ordering (not creation-ordering) sends skipped or demoted work
    to the back of the reserve, so a skip always surfaces a *different*
    task when one is waiting.
    """
    nxt = (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.status == TaskStatus.QUEUED)
        .order_by(Task.updated_at.asc(), Task.id.asc())
        .first()
    )
    if nxt is not None:
        guard.activate_task(db, nxt)
    return nxt


def _owned_task_or_404(db: Session, user_id: int, task_id: int) -> Task:
    task = (
        db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/focus", response_model=FocusOut)
def read_focus(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    active = guard.get_active_task(db, user_id)
    return FocusOut(
        selected_task=task_out(active) if active is not None else None,
        queued_backlog_count=_reserve_count(db, user_id),
    )


@router.post("/tasks/{task_id}/complete", response_model=CompleteOut)
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    task = _owned_task_or_404(db, user_id, task_id)
    if task.status is TaskStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Archived tasks cannot be completed")

    already_completed = task.status is TaskStatus.COMPLETED
    if not already_completed:
        guard.set_status(db, task, TaskStatus.COMPLETED)

    active = guard.get_active_task(db, user_id)
    if active is None:
        active = _promote_next_queued(db, user_id)
    db.commit()

    rhythm = suggest_context(db, user_id)
    return CompleteOut(
        task=task_out(task),
        next_task=task_out(active) if active is not None else None,
        queued_backlog_count=_reserve_count(db, user_id),
        already_completed=already_completed,
        rhythm=RhythmOut(**rhythm),
    )


@router.post("/tasks/{task_id}/skip", response_model=SkipOut)
def skip_task(
    task_id: int,
    mode: Literal["archive", "reserve"] = "reserve",
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    task = _owned_task_or_404(db, user_id, task_id)
    if task.status is TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Completed tasks cannot be skipped")

    already_archived = task.status is TaskStatus.ARCHIVED
    if not already_archived:
        target = TaskStatus.ARCHIVED if mode == "archive" else TaskStatus.QUEUED
        guard.set_status(db, task, target)

    active = guard.get_active_task(db, user_id)
    if active is None:
        active = _promote_next_queued(db, user_id)
    db.commit()

    return SkipOut(
        task=task_out(task),
        next_task=task_out(active) if active is not None else None,
        queued_backlog_count=_reserve_count(db, user_id),
        already_archived=already_archived,
        mode=mode,
    )
