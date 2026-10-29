"""Single-active task state machine (Invariant 1).

Every transition into ``in_progress`` — whether a brand-new insert or a
status update on an existing row — must pass through
:class:`SingleActiveTaskGuard`. The guard demotes any other active task
belonging to the same user (default: back to the hidden ``queued``
reserve) so that at most ONE task per user holds
``status == 'in_progress'`` at any time, and records each demotion in
:attr:`InvariantLog <app.models.InvariantLog>`.

The guard flushes but never commits: the caller owns the transaction and
decides when to commit or roll back.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import InvariantLog, Task, TaskStatus

INVARIANT_NAME = "single_active_task"

DEMOTE_TARGETS = (TaskStatus.QUEUED, TaskStatus.ARCHIVED)


class SingleActiveTaskGuard:
    """Strict enforcement engine for the single-active-task invariant."""

    def __init__(self, demote_to: TaskStatus = TaskStatus.QUEUED) -> None:
        target = TaskStatus(demote_to)
        if target not in DEMOTE_TARGETS:
            raise ValueError(f"demote_to must be one of {DEMOTE_TARGETS}, got {target!r}")
        self.demote_to = target

    def get_active_task(self, db: Session, user_id: int) -> Task | None:
        """Return the user's current in-progress task, if any."""
        return (
            db.query(Task)
            .filter(Task.user_id == user_id, Task.status == TaskStatus.IN_PROGRESS)
            .order_by(Task.updated_at.desc(), Task.id.desc())
            .first()
        )

    def promote_next(
        self, db: Session, user_id: int, exclude_id: int | None = None
    ) -> Task | None:
        """Surface the least-recently-touched reserve task as active.

        Touch-ordering sends skipped or demoted work to the back, and
        ``exclude_id`` (the just-skipped task) keeps a skip with an empty
        reserve from re-activating the same row: promotion then settles to
        ``None`` and the surface honestly empties. WhatsApp, web, and watch
        share this ordering so every surface hands back the same "next".
        """
        query = (
            db.query(Task)
            .filter(Task.user_id == user_id, Task.status == TaskStatus.QUEUED)
            .order_by(Task.updated_at.asc(), Task.id.asc())
        )
        if exclude_id is not None:
            query = query.filter(Task.id != exclude_id)
        nxt = query.first()
        if nxt is not None:
            self.activate_task(db, nxt)
        return nxt

    def activate_task(
        self,
        db: Session,
        task: Task,
        *,
        demote_to: TaskStatus | None = None,
    ) -> list[Task]:
        """Move ``task`` to ``in_progress``, demoting any rival active task.

        Returns the list of demoted tasks (empty when there was no rival).
        Repairs legacy violations too: if several rivals exist, all of them
        are demoted, keeping only ``task`` active.
        """
        target = TaskStatus(demote_to) if demote_to is not None else self.demote_to
        if target not in DEMOTE_TARGETS:
            raise ValueError(f"demote_to must be one of {DEMOTE_TARGETS}, got {target!r}")
        if task.user_id is None:
            raise ValueError("Task must belong to a user before activation")

        db.add(task)
        db.flush()  # ensure identity so the rival query can exclude this row

        rivals = (
            db.query(Task)
            .filter(
                Task.user_id == task.user_id,
                Task.status == TaskStatus.IN_PROGRESS,
                Task.id != task.id,
            )
            .order_by(Task.updated_at.desc(), Task.id.desc())
            .all()
        )
        for rival in rivals:
            rival.status = target
            db.add(
                InvariantLog(
                    user_id=task.user_id,
                    invariant=INVARIANT_NAME,
                    action="demote",
                    detail=(
                        f"task {rival.id} in_progress->{target.value}, "
                        f"superseded by task {task.id}"
                    ),
                )
            )

        task.status = TaskStatus.IN_PROGRESS
        # Fresh stall episode for this activation (Invariant 5).
        task.last_nudged_at = None
        task.nudge_silenced = False
        db.flush()
        return rivals

    def set_status(self, db: Session, task: Task, new_status: TaskStatus | str) -> list[Task]:
        """Set a task's status, routing ``in_progress`` through the guard.

        Returns the list of tasks demoted as a side effect (non-empty only
        when ``new_status`` is ``in_progress`` and a rival was active).
        """
        status = TaskStatus(new_status)
        if status is TaskStatus.IN_PROGRESS:
            return self.activate_task(db, task)
        task.status = status
        if status is TaskStatus.COMPLETED:
            task.completed_at = datetime.now(timezone.utc)
        db.flush()
        return []
