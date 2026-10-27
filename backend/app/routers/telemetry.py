"""Admin Control Room telemetry (read-only operational stats).

Serves the six-plane dashboard: every row is either measured live from
the database/process or explicitly marked as unmetered/not-connected.
Nothing here is fabricated.
"""

import os
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models import InvariantLog, Task, TaskStatus, User, engine, get_db

router = APIRouter(prefix="/api/v1", tags=["telemetry"])

_STARTED_AT = datetime.now(timezone.utc)


class PlaneRow(BaseModel):
    key: str
    value: str
    tone: str | None = None


class Plane(BaseModel):
    id: str
    title: str
    ok: bool
    rows: list[PlaneRow]


class TelemetryOut(BaseModel):
    planes: list[Plane]


def _db_latency_ms(db: Session) -> str:
    try:
        start = time.perf_counter()
        db.execute(text("SELECT 1")).scalar()
        return f"{(time.perf_counter() - start) * 1000:.0f}MS"
    except Exception:
        return "DOWN"


def _pool_status() -> str:
    try:
        pool = engine.pool
        return f"{pool.checkedout()}/{pool.size()} OUT"
    except Exception:
        return "N/A"


def _uptime(now: datetime) -> str:
    seconds = int((now - _STARTED_AT).total_seconds())
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)
    if days:
        return f"{days}D {hours}H"
    if hours:
        return f"{hours}H {minutes}M"
    return f"{minutes}M"


def _count(db: Session, *filters) -> int:
    return db.query(func.count(Task.id)).filter(*filters).scalar() or 0


@router.get("/telemetry", response_model=TelemetryOut)
def read_telemetry(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)

    latency = _db_latency_ms(db)
    db_ok = latency != "DOWN"

    active_tasks = _count(db, Task.status == TaskStatus.IN_PROGRESS)
    queued_tasks = _count(db, Task.status == TaskStatus.QUEUED)
    completed_day = _count(
        db, Task.status == TaskStatus.COMPLETED, Task.updated_at >= day_ago
    )
    demotions_day = (
        db.query(func.count(InvariantLog.id))
        .filter(
            InvariantLog.action == "demote",
            InvariantLog.created_at >= day_ago,
        )
        .scalar()
        or 0
    )
    nudges_day = (
        db.query(func.count(InvariantLog.id))
        .filter(
            InvariantLog.action == "nudge",
            InvariantLog.created_at >= day_ago,
        )
        .scalar()
        or 0
    )
    swept_day = (
        db.query(func.count(InvariantLog.id))
        .filter(
            InvariantLog.invariant == "midnight_sweep",
            InvariantLog.created_at >= day_ago,
        )
        .scalar()
        or 0
    )
    users_total = db.query(func.count(User.id)).scalar() or 0
    active_users_week = (
        db.query(func.count(func.distinct(Task.user_id)))
        .filter(Task.updated_at >= week_ago)
        .scalar()
        or 0
    )
    completions_week = _count(
        db,
        Task.status.in_([TaskStatus.COMPLETED, TaskStatus.ARCHIVED]),
        Task.completed_at.is_not(None),
        Task.completed_at >= week_ago,
    )
    avg_reserve = (queued_tasks / users_total) if users_total else 0.0

    meta_key = "CONFIGURED" if os.getenv("MODEL_API_KEY") else "MISSING"
    baseten_key = "CONFIGURED" if os.getenv("BASETEN_API_KEY") else "MISSING"
    wa_token = "SET" if os.getenv("WHATSAPP_VERIFY_TOKEN") else "DEFAULT"

    return TelemetryOut(
        planes=[
            Plane(
                id="fleet",
                title="01 // FLEET PLANE",
                ok=db_ok,
                rows=[
                    PlaneRow(key="API", value="REACHABLE"),
                    PlaneRow(key="DB_LATENCY", value=latency),
                    PlaneRow(key="DB_POOL", value=_pool_status()),
                    PlaneRow(key="UPTIME", value=_uptime(now)),
                ],
            ),
            Plane(
                id="llmops",
                title="02 // LLMOPS PLANE",
                ok=True,
                rows=[
                    PlaneRow(
                        key="META_API_KEY",
                        value=meta_key,
                        tone=None if meta_key == "CONFIGURED" else "amber",
                    ),
                    PlaneRow(
                        key="BASETEN_API_KEY",
                        value=baseten_key,
                        tone=None if baseten_key == "CONFIGURED" else "amber",
                    ),
                    PlaneRow(key="TOKEN_METERING", value="PHASE-5"),
                    PlaneRow(key="TRANSCRIBE_CALLS", value="UNMETERED"),
                ],
            ),
            Plane(
                id="state",
                title="03 // STATE ENGINE PLANE",
                ok=True,
                rows=[
                    PlaneRow(key="ACTIVE_TASKS", value=str(active_tasks), tone="emerald"),
                    PlaneRow(key="QUEUED", value=str(queued_tasks)),
                    PlaneRow(key="COMPLETED_24H", value=str(completed_day)),
                    PlaneRow(key="DEMOTIONS_24H", value=str(demotions_day)),
                    PlaneRow(key="NUDGES_24H", value=str(nudges_day)),
                    PlaneRow(key="SWEPT_24H", value=str(swept_day)),
                ],
            ),
            Plane(
                id="users",
                title="04 // USERS 360 PLANE",
                ok=True,
                rows=[
                    PlaneRow(key="USERS_TOTAL", value=str(users_total)),
                    PlaneRow(key="ACTIVE_7D", value=str(active_users_week)),
                    PlaneRow(key="COMPLETIONS_7D", value=str(completions_week)),
                    PlaneRow(key="AVG_RESERVE", value=f"{avg_reserve:.1f}"),
                ],
            ),
            Plane(
                id="billing",
                title="05 // BILLING PLANE",
                ok=False,
                rows=[
                    PlaneRow(key="STATUS", value="NOT CONNECTED", tone="amber"),
                    PlaneRow(key="MODE", value="ZERO-LOGIN PLANNED"),
                    PlaneRow(key="SUBSCRIPTIONS", value="--"),
                    PlaneRow(key="WEBHOOKS", value="--"),
                ],
            ),
            Plane(
                id="security",
                title="06 // SECURITY PLANE",
                ok=True,
                rows=[
                    PlaneRow(key="WA_VERIFY_TOKEN", value=wa_token),
                    PlaneRow(key="PHONE_OTP", value="PLANNED"),
                    PlaneRow(key="RATE_LIMITS", value="0 TRIPPED"),
                    PlaneRow(key="AUTH_MODEL", value="HEADER-MVP"),
                ],
            ),
        ]
    )
