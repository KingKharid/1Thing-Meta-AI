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
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.models import Task, TaskStatus, get_db, get_or_create_user
from app.services.rhythm import suggest_context
from app.services.state import SingleActiveTaskGuard
from app.services.triage import extract_or_fallback, triage

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


class TaskCreate(BaseModel):
    """Capture payload.

    Two shapes, one endpoint:

    - ``title``: one thing, as typed. The old contract, still used by
      surfaces that already know what the task is.
    - ``dump``: raw text, up to 8000 characters — a whole week of loose
      ends. The model decides how many tasks are actually in there.

    At least one of the two must be present. A blank title stays a 400
    (a person typed nothing meaningful); a body with neither field is a
    422 (the client sent the wrong shape).
    """

    title: str | None = Field(default=None, max_length=255)
    dump: str | None = Field(default=None, max_length=8000)
    first_micro_step: str = ""
    estimated_minutes: int = Field(default=15, gt=0)
    energy_required: Literal["low", "medium", "high"] = "medium"

    @model_validator(mode="after")
    def _has_text(self) -> "TaskCreate":
        if self.title is None and self.dump is None:
            raise ValueError("Provide either a title or a dump")
        return self


class TaskCreateOut(BaseModel):
    task: TaskOut
    active_task: TaskOut | None
    queued_backlog_count: int
    activated: bool
    # Who wrote the first step: the person typing, the model, the
    # verbatim heuristic fallback, or nobody. The UI needs this to avoid
    # claiming a step it does not have.
    step_source: Literal["user", "engine", "heuristic", "none"] = "none"
    # How many tasks this one message actually filed. A dump can be a
    # week of loose ends; the composer has to say so.
    filed_count: int = 1
    # Filed but parked in the hidden reserve rather than activated.
    stashed_count: int = 0


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


@router.post("/tasks", response_model=TaskCreateOut, status_code=201)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """File one thing, or a whole dump, from any capture surface.

    A ``dump`` is raw text — a week of loose ends in one message. The model
    reads it, extracts every distinct task, and orders them by what this
    person should do first given their real rhythm. Everything is stored;
    only the head of that order is activated, so the mountain is captured
    without ever being displayed.

    A step the person typed themselves is their own decomposition — honour
    it and skip the model.

    A dump is always extracted in full — never clipped to fit a title —
    through AI extraction with verbatim heuristic fallback, so a provider
    outage files the person's own words instead of losing the week.

    Two honest failure modes, deliberately different:

    - **dump**: nothing is filed and 503 comes back. The text stays in the
      composer; a half-read week would silently lose work. Reached only
      when even the heuristic finds nothing to file.
    - **title only**: the task is saved with an empty step, and
      ``step_source`` says ``none``. The card admits it has no step rather
      than borrowing one.
    """
    title = (payload.title or "").strip()
    dump = (payload.dump or "").strip()
    typed_step = payload.first_micro_step.strip()

    if not title and not dump:
        raise HTTPException(status_code=400, detail="Title must not be blank")

    step_source: Literal["user", "engine", "heuristic", "none"] = "none"
    entries: list[dict]

    if dump:
        full_text = f"{title}\n\n{dump}" if title else dump
        entries, used_fallback = extract_or_fallback(
            full_text, suggest_context(db, user_id)
        )
        if not entries:
            raise HTTPException(
                status_code=503,
                detail="The engine could not read this dump. Nothing was filed.",
            )
        if typed_step:
            entries[0]["first_micro_step"] = typed_step
            step_source = "user"
        else:
            step_source = "heuristic" if used_fallback else "engine"
    elif typed_step:
        entries = [
            {
                "title": title,
                "first_micro_step": typed_step,
                "estimated_minutes": payload.estimated_minutes,
                "energy_required": payload.energy_required,
            }
        ]
        step_source = "user"
    else:
        derived = triage(title, suggest_context(db, user_id))
        if derived is not None:
            entries = [derived]
            step_source = "engine"
        else:
            entries = [
                {
                    "title": title,
                    "first_micro_step": "",
                    "estimated_minutes": payload.estimated_minutes,
                    "energy_required": payload.energy_required,
                }
            ]

    # Insert in the model's order. Auto-increment ids therefore preserve
    # priority, which is what the reserve promotes by.
    tasks: list[Task] = []
    for entry in entries:
        task = Task(
            user_id=user_id,
            title=entry["title"],
            first_micro_step=entry["first_micro_step"],
            estimated_minutes=entry["estimated_minutes"],
            energy_required=entry["energy_required"],
            status=TaskStatus.QUEUED,
        )
        db.add(task)
        tasks.append(task)
    db.flush()

    # Never yank a task the person is already mid-step on. The dump waits
    # in the reserve until the current one is done or skipped.
    active = guard.get_active_task(db, user_id)
    activated = False
    if active is None and tasks:
        guard.activate_task(db, tasks[0])
        active = tasks[0]
        activated = True
    db.commit()

    return TaskCreateOut(
        task=task_out(tasks[0]),
        active_task=task_out(active) if active is not None else None,
        queued_backlog_count=_reserve_count(db, user_id),
        activated=activated,
        step_source=step_source,
        filed_count=len(tasks),
        stashed_count=len(tasks) - (1 if activated else 0),
    )


@router.post("/tasks/{task_id}/derive", response_model=TaskOut)
def derive_step(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Re-run triage for a task that has no step.

    Covers two honest cases: a task filed while the model was down, and
    tasks that predate the model being called on this path. 503 is the
    truthful answer when the engine still cannot produce one — the card
    keeps saying it has no step.
    """
    task = _owned_task_or_404(db, user_id, task_id)
    if task.status is TaskStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Archived tasks cannot be revised")

    derived = triage(task.title, suggest_context(db, user_id))
    if derived is None:
        raise HTTPException(
            status_code=503, detail="The engine did not return a first step"
        )

    if derived["title"]:
        task.title = derived["title"]
    task.first_micro_step = derived["first_micro_step"]
    task.estimated_minutes = derived["estimated_minutes"]
    task.energy_required = derived["energy_required"]
    db.commit()
    return task_out(task)


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
        active = guard.promote_next(db, user_id)
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
        # Never re-activate the just-skipped row: with an empty reserve
        # the surface honestly empties (next_task null).
        active = guard.promote_next(db, user_id, exclude_id=task.id)
    db.commit()

    return SkipOut(
        task=task_out(task),
        next_task=task_out(active) if active is not None else None,
        queued_backlog_count=_reserve_count(db, user_id),
        already_archived=already_archived,
        mode=mode,
    )
