import os
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.meta_client import (
    transcribe_audio_dump,
    segment_visual_note,
    evaluate_single_task_meta,
    evaluate_single_task_baseten
)
from app.models import SessionLocal, Task, TaskStatus, get_or_create_user, init_db
from app.routers import focus as focus_router
from app.routers import telemetry as telemetry_router
from app.services.state import SingleActiveTaskGuard

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
            if msg.get("type") == "text":
                text_content = msg["text"]["body"]
                user_id = msg.get("from", "unknown")
                background_tasks.add_task(handle_pipeline, text_content, "meta", user_id)
    except Exception as e:
        print(f"Webhook parse error: {e}")
    return {"status": "received"}


def _safe_minutes(value: object) -> int:
    try:
        minutes = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 15
    return minutes if minutes > 0 else 15


def _safe_energy(value: object) -> str:
    return value if value in ("low", "medium", "high") else "medium"


def handle_pipeline(raw_text: str, engine: str = "meta", user_id: str = "unknown"):
    context = {"available_minutes": 25, "energy": "medium", "time_of_day": "morning"}
    if engine == "baseten":
        result = evaluate_single_task_baseten(raw_text, context)
    else:
        result = evaluate_single_task_meta(raw_text, context)

    # Persist the selected task. The guard enforces Invariant 1: any
    # previously active task is demoted to the hidden reserve, so the
    # client payload exposes the new task plus a reserve *count* only.
    selected = result.get("selected_task", {}) or {}
    db: Session = SessionLocal()
    try:
        user = get_or_create_user(db, phone_number=user_id)
        task = Task(
            user_id=user.id,
            title=str(selected.get("title") or raw_text[:120] or "Untitled task"),
            first_micro_step=str(selected.get("first_micro_step") or ""),
            estimated_minutes=_safe_minutes(selected.get("estimated_minutes")),
            energy_required=_safe_energy(selected.get("energy_required")),
        )
        demoted = invariant_guard.activate_task(db, task)
        db.commit()
        reserve_count = (
            db.query(Task)
            .filter(Task.user_id == user.id, Task.status == TaskStatus.QUEUED)
            .count()
        )
        result["selected_task"] = {
            "id": task.id,
            "title": task.title,
            "first_micro_step": task.first_micro_step,
            "estimated_minutes": task.estimated_minutes,
            "energy_required": task.energy_required,
        }
        result["queued_backlog_count"] = reserve_count
        result["demoted_task_ids"] = [t.id for t in demoted]
    finally:
        db.close()

    print("=== 1THING EXECUTION RESULT ===")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
