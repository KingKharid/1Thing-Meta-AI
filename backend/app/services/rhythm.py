"""User rhythm learner: time-of-day energy weighting engine.

Learns, per user, which energy levels historically convert to completions
in each time-of-day bucket, so the pipeline can bias the single-task
decision toward work the user can actually start right now.

Signal: ``completed`` tasks plus swept tasks that carry a
``completed_at`` timestamp (served, then archived at midnight). Stale
archives carry no completion signal and are excluded.

Use :func:`suggest_context` to build the ``user_context`` payload that
``evaluate_single_task_*`` consumes; it matches the pipeline shape
(``available_minutes`` / ``energy`` / ``time_of_day``).
"""

from collections import Counter
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import Task, TaskStatus

ENERGY_LEVELS = ("low", "medium", "high")

# (bucket, start_inclusive, end_exclusive). "night" wraps midnight.
TIME_BUCKETS: tuple[tuple[str, time, time], ...] = (
    ("morning", time(5, 0), time(12, 0)),
    ("afternoon", time(12, 0), time(17, 0)),
    ("evening", time(17, 0), time(22, 0)),
    ("night", time(22, 0), time(5, 0)),
)


def bucket_for(moment: datetime) -> str:
    """Map a timestamp to its time-of-day bucket."""
    moment_t = moment.time().replace(tzinfo=None)
    for name, start, end in TIME_BUCKETS:
        if start <= end:
            if start <= moment_t < end:
                return name
        elif moment_t >= start or moment_t < end:
            return name
    raise AssertionError(f"unreachable hour: {moment_t!r}")  # buckets cover 24h


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _resolve_tz(tz: ZoneInfo | timezone | None) -> timezone | ZoneInfo:
    return tz if tz is not None else timezone.utc


def _completion_moments(db: Session, user_id: int) -> list[tuple[datetime, str]]:
    """Return ``(completed_at, energy)`` pairs carrying a real signal."""
    tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.status.in_([TaskStatus.COMPLETED, TaskStatus.ARCHIVED]),
        )
        .all()
    )
    moments = []
    for task in tasks:
        moment = task.completed_at or task.updated_at
        if task.completed_at is None and task.status is TaskStatus.ARCHIVED:
            continue  # stale archive: swept without ever being served
        if task.energy_required in ENERGY_LEVELS:
            moments.append((moment, task.energy_required))
    return moments


def learn_energy_profile(
    db: Session,
    user_id: int,
    *,
    tz: ZoneInfo | timezone | None = None,
    smoothing: float = 1.0,
) -> dict[str, dict[str, float]]:
    """Learn per-bucket energy weights from completion history.

    Laplace smoothing keeps cold-start and sparse buckets near-uniform
    instead of collapsing to zero. Each bucket's weights sum to 1.0.
    """
    zone = _resolve_tz(tz)
    counts: dict[str, Counter] = {name: Counter() for name, _, _ in TIME_BUCKETS}
    for moment, energy in _completion_moments(db, user_id):
        counts[bucket_for(_as_utc(moment).astimezone(zone))][energy] += 1
    return {
        bucket: {
            energy: (counts[bucket][energy] + smoothing)
            / (sum(counts[bucket].values()) + smoothing * len(ENERGY_LEVELS))
            for energy in ENERGY_LEVELS
        }
        for bucket in counts
    }


def recommend_energy(
    db: Session,
    user_id: int,
    *,
    now: datetime | None = None,
    tz: ZoneInfo | timezone | None = None,
) -> str:
    """Recommend the best energy level for the user's current bucket.

    Ties resolve deterministically toward the first level in
    ``ENERGY_LEVELS`` (cold start therefore recommends ``"low"``).
    """
    zone = _resolve_tz(tz)
    current = _as_utc(now or datetime.now(timezone.utc)).astimezone(zone)
    weights = learn_energy_profile(db, user_id, tz=zone)[bucket_for(current)]
    return max(ENERGY_LEVELS, key=lambda level: weights[level])


def score_energy(
    db: Session,
    user_id: int,
    energy: str,
    *,
    now: datetime | None = None,
    tz: ZoneInfo | timezone | None = None,
) -> float:
    """Return the current-bucket weight for one energy level (0.0-1.0)."""
    zone = _resolve_tz(tz)
    current = _as_utc(now or datetime.now(timezone.utc)).astimezone(zone)
    return learn_energy_profile(db, user_id, tz=zone)[bucket_for(current)][energy]


def suggest_context(
    db: Session,
    user_id: int,
    *,
    now: datetime | None = None,
    tz: ZoneInfo | timezone | None = None,
    available_minutes: int = 25,
) -> dict:
    """Build a pipeline-ready ``user_context`` for this user and moment."""
    zone = _resolve_tz(tz)
    current = _as_utc(now or datetime.now(timezone.utc)).astimezone(zone)
    return {
        "available_minutes": available_minutes,
        "energy": recommend_energy(db, user_id, now=current, tz=zone),
        "time_of_day": bucket_for(current),
    }
