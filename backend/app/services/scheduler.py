"""Background scheduling: midnight sweep and stall nudges.

Invariants covered:
- Invariant 4 (Midnight sweep): served/skipped (``completed``) work is
  archived silently at local midnight; untouched ``queued`` items older
  than seven days follow. No guilt copy.
- Invariant 5 (One nudge, then silence): exactly one check-in after 180
  stalled minutes on the active task, then total silence once 45 more
  minutes pass without progress.

All functions are pure decisions plus state mutations: they never send
notifications themselves. The caller delivers check-ins (WhatsApp/push)
for the ids returned by :func:`stall_nudge_check`, and invokes
:func:`midnight_sweep` from a cron worker scoped (via ``user_ids``) to
users sharing a local midnight.

Like the state guard, these functions flush but never commit: the caller
owns the transaction.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import InvariantLog, Task, TaskStatus

STALE_QUEUED_DAYS = 7
STALL_MINUTES = 180
SILENCE_AFTER_MINUTES = 45

SWEEP_INVARIANT = "midnight_sweep"
NUDGE_INVARIANT = "stall_nudge"


def _ensure_aware(value: datetime) -> datetime:
    """Normalize ``now`` overrides to aware UTC for portable comparison."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _scoped(query, user_ids: list[int] | None):
    if user_ids is not None:
        return query.filter(Task.user_id.in_(user_ids))
    return query


def archive_served_tasks(db: Session, *, user_ids: list[int] | None = None) -> list[Task]:
    """Archive ``completed`` (served/skipped) work. Returns archived tasks."""
    archived = _scoped(db.query(Task).filter(Task.status == TaskStatus.COMPLETED), user_ids).all()
    for task in archived:
        task.status = TaskStatus.ARCHIVED
        db.add(
            InvariantLog(
                user_id=task.user_id,
                invariant=SWEEP_INVARIANT,
                action="archive",
                detail=f"task {task.id} completed->archived at midnight sweep",
            )
        )
    db.flush()
    return archived


def archive_stale_queued(
    db: Session,
    *,
    now: datetime | None = None,
    stale_days: int = STALE_QUEUED_DAYS,
    user_ids: list[int] | None = None,
) -> list[Task]:
    """Archive ``queued`` tasks untouched for ``stale_days``. Returns archived tasks."""
    cutoff = _ensure_aware(now or _utcnow()) - timedelta(days=stale_days)
    stale = _scoped(
        db.query(Task).filter(Task.status == TaskStatus.QUEUED, Task.updated_at <= cutoff),
        user_ids,
    ).all()
    for task in stale:
        task.status = TaskStatus.ARCHIVED
        db.add(
            InvariantLog(
                user_id=task.user_id,
                invariant=SWEEP_INVARIANT,
                action="archive",
                detail=f"task {task.id} queued->archived untouched for {stale_days}d",
            )
        )
    db.flush()
    return stale


def midnight_sweep(
    db: Session,
    *,
    now: datetime | None = None,
    user_ids: list[int] | None = None,
) -> dict[str, list[int]]:
    """Run the full midnight sweep. Active tasks are never swept.

    Returns ``{"archived_served": [...], "archived_stale": [...]}`` id lists.
    """
    served = archive_served_tasks(db, user_ids=user_ids)
    stale = archive_stale_queued(db, now=now, user_ids=user_ids)
    return {
        "archived_served": [t.id for t in served],
        "archived_stale": [t.id for t in stale],
    }


def stall_nudge_check(
    db: Session,
    *,
    now: datetime | None = None,
    stall_minutes: int = STALL_MINUTES,
    silence_after_minutes: int = SILENCE_AFTER_MINUTES,
    user_ids: list[int] | None = None,
) -> dict[str, list[int]]:
    """Fire at most one check-in per active stall episode, then silence.

    - Active task untouched for ``stall_minutes`` with no nudge yet: nudge.
    - Nudged task still active ``silence_after_minutes`` later: silence
      (no further check-ins until the task is re-activated).
    - All other active tasks: untouched.

    Nudge state is written via bulk updates so the ``updated_at`` stall
    clock keeps measuring user activity, not scheduler writes.

    Returns ``{"nudged": [...], "silenced": [...]}`` id lists. The caller
    delivers the check-in for each nudged id.
    """
    current = _ensure_aware(now or _utcnow())
    stalled_before = current - timedelta(minutes=stall_minutes)
    silence_before = current - timedelta(minutes=silence_after_minutes)

    to_nudge = _scoped(
        db.query(Task).filter(
            Task.status == TaskStatus.IN_PROGRESS,
            Task.updated_at <= stalled_before,
            Task.last_nudged_at.is_(None),
            Task.nudge_silenced.is_(False),
        ),
        user_ids,
    ).all()
    to_silence = _scoped(
        db.query(Task).filter(
            Task.status == TaskStatus.IN_PROGRESS,
            Task.last_nudged_at.is_not(None),
            Task.last_nudged_at <= silence_before,
            Task.nudge_silenced.is_(False),
        ),
        user_ids,
    ).all()

    nudged_ids = [t.id for t in to_nudge]
    silenced_ids = [t.id for t in to_silence]

    if nudged_ids:
        for task in to_nudge:
            # Explicit updated_at wins over the column onupdate hook, so the
            # stall clock keeps measuring user activity, not scheduler writes.
            db.query(Task).filter_by(id=task.id).update(
                {"last_nudged_at": current, "updated_at": task.updated_at},
                synchronize_session=False,
            )
            db.add(
                InvariantLog(
                    user_id=task.user_id,
                    invariant=NUDGE_INVARIANT,
                    action="nudge",
                    detail=f"task {task.id} stalled {stall_minutes}m, check-in sent",
                )
            )
    if silenced_ids:
        for task in to_silence:
            db.query(Task).filter_by(id=task.id).update(
                {"nudge_silenced": True, "updated_at": task.updated_at},
                synchronize_session=False,
            )
            db.add(
                InvariantLog(
                    user_id=task.user_id,
                    invariant=NUDGE_INVARIANT,
                    action="nudge_silence",
                    detail=(
                        f"task {task.id} still stalled "
                        f"{silence_after_minutes}m after nudge, silenced"
                    ),
                )
            )
    db.flush()
    return {"nudged": nudged_ids, "silenced": silenced_ids}
