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
from app.services.auth import require_admin
from app.services.ratelimit import limiter
from app.services.triage import PRIMARY_ENGINE

router = APIRouter(
    prefix="/api/v1", tags=["telemetry"], dependencies=[Depends(require_admin)]
)

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


def _ago(when: datetime | None, now: datetime) -> str:
    """Human age of a log row. Naive SQLite timestamps are treated as UTC."""
    if when is None:
        return "NEVER"
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    seconds = max(0, int((now - when).total_seconds()))
    if seconds < 60:
        return f"{seconds}S AGO"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}M AGO"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}H AGO"
    return f"{hours // 24}D AGO"


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
    baseten_calls_day = (
        db.query(func.count(InvariantLog.id))
        .filter(
            InvariantLog.invariant == "model_routing",
            InvariantLog.action == "baseten_ok",
            InvariantLog.created_at >= day_ago,
        )
        .scalar()
        or 0
    )
    meta_calls_day = (
        db.query(func.count(InvariantLog.id))
        .filter(
            InvariantLog.invariant == "model_routing",
            InvariantLog.action == "meta_ok",
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
    wa_access = "SET" if os.getenv("WHATSAPP_ACCESS_TOKEN") else "MISSING"
    wa_phone = "SET" if os.getenv("WHATSAPP_PHONE_NUMBER_ID") else "MISSING"
    scheduler_on = (os.getenv("RUN_SCHEDULER") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    media_model = os.getenv("META_VOICE_MODEL", "muse-wonder-1.0")

    # Which engine answered most recently. Counts alone cannot distinguish
    # "Baseten is primary" from "Baseten was primary once"; recency can.
    last_routing = (
        db.query(InvariantLog)
        .filter(InvariantLog.invariant == "model_routing")
        .order_by(InvariantLog.created_at.desc(), InvariantLog.id.desc())
        .first()
    )
    if last_routing is None:
        last_engine = "NONE YET"
        last_engine_tone = "amber"
        last_engine_model = "—"
        last_engine_age = "NEVER"
    else:
        provider, _, outcome = last_routing.action.rpartition("_")
        last_engine = f"{provider.upper()} // {outcome.upper()}"
        last_engine_tone = "emerald" if outcome == "ok" else "amber"
        last_engine_model = (
            os.getenv("BASETEN_MODEL", "meta-models/muse-spark-open-1026")
            if provider == "baseten"
            else os.getenv("META_MODEL", "muse-spark-1.3")
        )
        last_engine_age = _ago(last_routing.created_at, now)

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
                    PlaneRow(
                        key="SCHEDULER",
                        value="RUNNING" if scheduler_on else "OFF",
                        tone="emerald" if scheduler_on else "amber",
                    ),
                ],
            ),
            Plane(
                id="llmops",
                title="02 // LLMOPS PLANE",
                ok=True,
                rows=[
                    PlaneRow(
                        key="PRIMARY_ENGINE",
                        value=f"{PRIMARY_ENGINE.upper()} // OPEN WEIGHTS",
                        tone="emerald" if PRIMARY_ENGINE == "baseten" else None,
                    ),
                    PlaneRow(
                        key="LAST_ENGINE",
                        value=last_engine,
                        tone=last_engine_tone,
                    ),
                    PlaneRow(key="ENGINE_MODEL", value=last_engine_model),
                    PlaneRow(key="LAST_ENGINE_AGE", value=last_engine_age),
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
                    PlaneRow(
                        key="BASETEN_CALLS_24H",
                        value=str(baseten_calls_day),
                        tone="emerald" if baseten_calls_day else None,
                    ),
                    PlaneRow(key="META_CALLS_24H", value=str(meta_calls_day)),
                    PlaneRow(key="MEDIA_MODEL", value=media_model),
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
                    PlaneRow(
                        key="WA_ACCESS_TOKEN",
                        value=wa_access,
                        tone=None if wa_access == "SET" else "amber",
                    ),
                    PlaneRow(
                        key="WA_PHONE_ID",
                        value=wa_phone,
                        tone=None if wa_phone == "SET" else "amber",
                    ),
                    PlaneRow(key="ADMIN_AUTH", value="X-ADMIN-KEY"),
                    PlaneRow(key="PHONE_OTP", value="NOT BUILT", tone="amber"),
                    PlaneRow(
                        key="RATE_LIMITS",
                        value=(
                            "OFF"
                            if limiter.limit <= 0
                            else f"{limiter.limit}/MIN"
                        ),
                        tone=None if limiter.limit > 0 else "amber",
                    ),
                    PlaneRow(key="AUTH_MODEL", value="HEADER-MVP", tone="amber"),
                ],
            ),
        ]
    )
