import os
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.models import SessionLocal, Task, TaskStatus, get_or_create_user, init_db
from app.routers import focus as focus_router
from app.routers import telemetry as telemetry_router
from app.services import whatsapp_templates
from app.services.rhythm import suggest_context
from app.services.state import SingleActiveTaskGuard
from app.services.triage import extract_or_fallback
from app.services.whatsapp_client import send_focus_message, send_text

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "one_thing_hackathon_verify_token_2026")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="1Thing Meta AI Executive Core", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Invariant 1 engine: superseded tasks fall back to the hidden reserve.
invariant_guard = SingleActiveTaskGuard(demote_to=TaskStatus.QUEUED)

app.include_router(focus_router.router)
app.include_router(telemetry_router.router)


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "operational",
        "engine": "1Thing Warm Industrial Core",
        "active_invariants": 7
    }


@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), status_code=200)
    return Response(content="Verification failed", status_code=403)


@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    try:
        messages = data["entry"][0]["changes"][0]["value"].get("messages", [])
        if messages:
            msg = messages[0]
            user_id = msg.get("from", "unknown")
            kind = msg.get("type")

            if kind == "text":
                text_content = msg["text"]["body"]
                # Exact DONE/SKIP only: a dump that merely mentions the
                # word "done" still goes through the triage pipeline.
                command = whatsapp_templates.command_of(text_content)
                if command:
                    background_tasks.add_task(handle_command, command, user_id, None)
                else:
                    background_tasks.add_task(handle_pipeline, text_content, "meta", user_id)

            elif kind == "interactive":
                reply = (msg.get("interactive") or {}).get("button_reply") or {}
                command, task_id = whatsapp_templates.command_from_button(
                    str(reply.get("id") or "")
                )
                if command:
                    background_tasks.add_task(handle_command, command, user_id, task_id)

            elif kind in ("audio", "image", "video", "document"):
                # Media transcription lands with the Modal pipeline. Say so
                # instead of dropping the message into silence.
                background_tasks.add_task(handle_media, kind, user_id)
    except Exception as e:
        print(f"Webhook parse error: {e}")
    return {"status": "received"}


def _task_brief(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "first_micro_step": task.first_micro_step,
        "estimated_minutes": task.estimated_minutes,
        "energy_required": task.energy_required,
    }


def _reserve_count(db: Session, user_id: int) -> int:
    return (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.status == TaskStatus.QUEUED)
        .count()
    )


def _deliver(user_id: str, body: str) -> bool:
    """Send a reply. Never raises; unconfigured channels no-op."""
    if not user_id or user_id == "unknown" or not body:
        return False
    return send_text(user_id, body)


def _deliver_focus(user_id: str, body: str, task_id: int | None) -> bool:
    """Send the focus reply with DONE/SKIP buttons when a task id exists."""
    if not user_id or user_id == "unknown" or not body:
        return False
    if task_id is None:
        return send_text(user_id, body)
    return send_focus_message(user_id, body, task_id)


def handle_media(kind: str, user_id: str = "unknown") -> None:
    """Honest reply for media the pipeline cannot read yet.

    Voice notes and photos are ingested through the Modal media pipeline
    in a later phase. Silence is the worst possible answer, so the user
    gets a plain statement of what to do instead.
    """
    labels = {
        "audio": "voice notes",
        "image": "photos",
        "video": "video",
        "document": "files",
    }
    label = labels.get(kind, "that")
    _deliver(
        user_id,
        f"I cannot open {label} yet.\n"
        "Send it as text and I will return one physical next step.",
    )


def handle_pipeline(raw_text: str, engine: str = "meta", user_id: str = "unknown"):
    # First contact is decided before the LLM call so the onboarding line
    # can ride along with the first real reply.
    db: Session = SessionLocal()
    try:
        user = get_or_create_user(db, phone_number=user_id)
        user_pk = user.id
        first_contact = db.query(Task).filter(Task.user_id == user_pk).count() == 0
        # Real rhythm, not a fixed morning/medium/25. The model should see
        # the hour and energy this person actually works in.
        context = suggest_context(db, user_pk)
        db.commit()
    finally:
        db.close()

    tasks, _used_fallback = extract_or_fallback(raw_text, context, engine=engine)
    if not tasks:
        # Never leave the user in silence, and never invent a step.
        _deliver(user_id, whatsapp_templates.error_reply())
        return {}

    result = {"selected_task": tasks[0], "queued_backlog_count": 0}

    # Persist every extracted task, in the model's order, then activate only
    # the head. The guard enforces Invariant 1: any previously active task
    # is demoted to the hidden reserve, so the client payload exposes the
    # new task plus a reserve *count* only — a whole week's dump still shows
    # exactly one physical next step.
    db = SessionLocal()
    try:
        rows: list[Task] = []
        for entry in tasks:
            row = Task(
                user_id=user_pk,
                title=entry["title"] or raw_text[:120] or "Untitled task",
                first_micro_step=entry["first_micro_step"],
                estimated_minutes=entry["estimated_minutes"],
                energy_required=entry["energy_required"],
                status=TaskStatus.QUEUED,
            )
            db.add(row)
            rows.append(row)
        db.flush()

        demoted = invariant_guard.activate_task(db, rows[0])
        db.commit()
        reserve_count = _reserve_count(db, user_pk)
        result["selected_task"] = _task_brief(rows[0])
        result["queued_backlog_count"] = reserve_count
        result["filed_count"] = len(rows)
        result["stashed_count"] = max(0, len(rows) - 1)
        result["demoted_task_ids"] = [t.id for t in demoted]
        task_id = rows[0].id
    finally:
        db.close()

    print("=== 1THING EXECUTION RESULT ===")
    print(json.dumps(result, indent=2))

    # Reply in the user's own channel. A delivery failure must never roll
    # back or block the persisted state.
    try:
        if first_contact:
            _deliver(user_id, whatsapp_templates.onboarding_reply())
        _deliver_focus(
            user_id,
            whatsapp_templates.focus_reply(result, dump=raw_text),
            task_id,
        )
    except Exception as exc:  # pragma: no cover - defensive
        print(f"WhatsApp reply error: {exc}")

    return result


def handle_command(
    command: str, user_id: str = "unknown", expected_task_id: int | None = None
):
    """Handle an inbound DONE or SKIP from WhatsApp.

    Same state transitions as the focus router: DONE archives the active
    task and promotes the next reserve task; SKIP parks the active task
    back in the reserve. With nothing active, the reply is the standby
    template instead of an error.

    ``expected_task_id`` comes from the tapped button. A stale button (the
    surface moved on) re-renders the current task instead of mutating the
    wrong row.
    """
    db: Session = SessionLocal()
    try:
        user = get_or_create_user(db, phone_number=user_id)
        active = invariant_guard.get_active_task(db, user.id)

        if active is None:
            db.commit()
            _deliver(user_id, whatsapp_templates.idle_reply(_reserve_count(db, user.id)))
            return None

        if expected_task_id is not None and active.id != expected_task_id:
            reserve = _reserve_count(db, user.id)
            _deliver_focus(
                user_id,
                whatsapp_templates.current_reply(_task_brief(active), reserve),
                active.id,
            )
            return None

        if command == "DONE":
            invariant_guard.set_status(db, active, TaskStatus.COMPLETED)
        else:
            invariant_guard.set_status(db, active, TaskStatus.QUEUED)

        nxt = invariant_guard.get_active_task(db, user.id)
        if nxt is None:
            # A SKIP must never re-activate the just-skipped row: with an
            # empty reserve the surface honestly empties (next None).
            exclude = active.id if command == "SKIP" else None
            nxt = invariant_guard.promote_next(db, user.id, exclude_id=exclude)
        db.commit()

        result = {
            "task": _task_brief(active),
            "next_task": _task_brief(nxt) if nxt is not None else None,
            "queued_backlog_count": _reserve_count(db, user.id),
        }
        reply = (
            whatsapp_templates.completed_reply(result)
            if command == "DONE"
            else whatsapp_templates.skipped_reply(result)
        )
        _deliver_focus(user_id, reply, nxt.id if nxt is not None else None)
        return result
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
