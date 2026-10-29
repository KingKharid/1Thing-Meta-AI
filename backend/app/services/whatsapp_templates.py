"""WhatsApp response templates for the 1Thing conversational flow.

Pure formatting only: no database access, no network calls. Every
renderer accepts the same result shape that ``handle_pipeline`` and the
focus API already produce, so the webhook can send a reply without
reshaping a payload.

Design rules (Warm Industrial Minimalism, conversational register):
- Acknowledge the mess first. The user just handed over a lot.
- Surface exactly ONE task and ONE physical first step.
- Confirm the rest is *parked*, not deleted, using the reserve **count**
  only. Invariant 2: reserve titles are never rendered.
- No exclamation marks, no emoji, no shame. Calm and plain.
- Plain lines and ``*bold*`` only: ``_italic_`` and ``▸`` render
  inconsistently across WhatsApp clients.
"""

from __future__ import annotations

from typing import Any, Mapping

# WhatsApp caps a text body at 4096 chars. Stay well inside it.
MAX_BODY = 3900
MAX_TITLE = 72
MAX_STEP = 120

COMMANDS = ("DONE", "SKIP")

_LONG_DUMP_WORDS = 40


# --------------------------------------------------------------------- utils


def _clip(value: Any, limit: int) -> str:
    """Collapse whitespace and hard-clip, preserving word boundaries."""
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return number if number >= 0 else default


def _reserve_line(count: int, *, after: bool = False) -> str:
    """The reassurance line. Count only — never titles (Invariant 2)."""
    if count <= 0:
        return (
            "Nothing else is waiting."
            if after
            else "Nothing else is waiting — that dump was the whole list."
        )
    if count == 1:
        return "1 more, parked in the hidden reserve."
    return f"{count} more, parked in the hidden reserve."


def _finish(lines: list[str]) -> str:
    body = "\n".join(lines).strip()
    return body if len(body) <= MAX_BODY else body[: MAX_BODY - 1].rstrip() + "…"


def _acknowledge(dump: str | None) -> str:
    words = len((dump or "").split())
    if words >= _LONG_DUMP_WORDS:
        return "That was a big dump. All of it is captured."
    return "Got it. All of it is captured."


def _task_lines(
    task: Mapping[str, Any] | None, *, label: str, energy: str | None = None
) -> list[str]:
    if not task:
        return []
    title = _clip(task.get("title"), MAX_TITLE)
    step = _clip(task.get("first_micro_step"), MAX_STEP)
    minutes = _safe_int(task.get("estimated_minutes"), 15)

    lines = [f"*{label}*", title, ""]
    if step:
        lines += ["*FIRST STEP*", step, ""]
    meta = f"{minutes} MIN"
    if energy:
        meta += f" · {energy}"
    lines.append(meta)
    return lines


# ------------------------------------------------------------------ renderers


def onboarding_reply() -> str:
    """First contact: state the contract once, in three short lines."""
    return _finish(
        [
            "*1THING.*",
            "",
            "Send anything — a voice note, a photo, a messy paragraph.",
            "I reply with one physical next step.",
            "",
            "Everything else is parked in a hidden reserve. You only ever see one thing.",
        ]
    )


def focus_reply(
    result: Mapping[str, Any],
    *,
    dump: str | None = None,
    reasoning: str | None = None,
) -> str:
    """Reply after a messy dump has been triaged.

    ``result`` is the dict returned by ``handle_pipeline``:
    ``selected_task`` + ``queued_backlog_count``. ``reasoning`` is accepted
    for caller compatibility but no longer rendered: the reply is shorter
    than a chat bubble should be.
    """
    selected = result.get("selected_task") or {}
    if not selected or not selected.get("title"):
        return idle_reply(_safe_int(result.get("queued_backlog_count")))

    reserve = _safe_int(result.get("queued_backlog_count"))
    energy = str(selected.get("energy_required") or "medium").upper()

    lines = [_acknowledge(dump), ""]
    lines += _task_lines(selected, label="YOUR ONE THING", energy=energy)
    lines += ["", _reserve_line(reserve)]
    return _finish(lines)


def current_reply(task: Mapping[str, Any] | None, reserve_count: int = 0) -> str:
    """Re-render whatever is on the surface right now.

    Used when a stale button is tapped: the task moved, so show the current
    one instead of mutating the wrong row.
    """
    reserve = _safe_int(reserve_count)
    if not task:
        return idle_reply(reserve)
    lines = ["*ON YOUR SURFACE*", ""]
    lines += _task_lines(
        task,
        label="YOUR ONE THING",
        energy=str(task.get("energy_required") or "").upper() or None,
    )
    lines += ["", _reserve_line(reserve)]
    return _finish(lines)


def idle_reply(reserve_count: int = 0) -> str:
    """Reply when there is nothing active to show."""
    reserve = _safe_int(reserve_count)
    lines = [
        "*STANDBY.*",
        "",
        "Nothing is in focus right now.",
        "",
        "Send anything — voice, photo, or a messy paragraph — and I will "
        "pull out one next step.",
    ]
    if reserve > 0:
        lines += ["", _reserve_line(reserve)]
    return _finish(lines)


def completed_reply(result: Mapping[str, Any]) -> str:
    """Reply after a DONE. Surfaces the next task, or a clear surface."""
    reserve = _safe_int(result.get("queued_backlog_count"))
    nxt = result.get("next_task")

    lines = ["*DONE.*", ""]
    if nxt:
        lines += _task_lines(
            nxt, label="NEXT", energy=str(nxt.get("energy_required") or "").upper() or None
        )
        lines += ["", _reserve_line(reserve, after=True)]
    else:
        lines += [
            "That was the last thing on the surface.",
            "Nothing else is waiting. Send the next thought whenever you are ready.",
        ]
    return _finish(lines)


def skipped_reply(result: Mapping[str, Any]) -> str:
    """Reply after a SKIP. Parks the task without shame."""
    reserve = _safe_int(result.get("queued_backlog_count"))
    nxt = result.get("next_task")
    skipped = result.get("task") or {}

    # Defensive branch: promotion used to hand the same task back when
    # the reserve was empty. The backend now settles to next_task None
    # instead, but a same-title payload still renders honestly.
    if nxt and skipped and nxt.get("title") == skipped.get("title"):
        return _finish(
            [
                "*SKIPPED.* No shame — but it is the only thing waiting,",
                "so it stays on the surface.",
                "",
                "*TRY A SMALLER FIRST STEP*",
                _clip(nxt.get("first_micro_step"), MAX_STEP),
                "",
                "Shrink it until it takes two minutes.",
            ]
        )

    lines = ["*SKIPPED.* Parked, not deleted.", ""]
    if nxt:
        lines += _task_lines(
            nxt, label="NEXT", energy=str(nxt.get("energy_required") or "").upper() or None
        )
        lines += ["", _reserve_line(reserve, after=True)]
    else:
        lines += [
            "Your surface is clear for now.",
            _reserve_line(reserve, after=True),
        ]
    return _finish(lines)


def error_reply() -> str:
    """Reply when the dump could not be read. Reassure, never scold."""
    return _finish(
        [
            "I could not read that one.",
            "Nothing was lost — send it again as text, or try a shorter dump.",
        ]
    )


def command_of(text: str) -> str | None:
    """Return DONE/SKIP for an exact command, else None.

    Exact matching keeps a dump that merely *contains* the word "done"
    from being treated as a completion.
    """
    token = (text or "").strip().upper().strip(".!").strip()
    return token if token in COMMANDS else None


def command_from_button(payload_id: str) -> tuple[str | None, int | None]:
    """Parse an interactive button id such as ``done:42``.

    Returns ``(command, task_id)``; either may be None when the id is
    unrecognised or carries no task.
    """
    raw = (payload_id or "").strip()
    if not raw:
        return None, None
    head, _, tail = raw.partition(":")
    command = head.strip().upper()
    if command not in COMMANDS:
        return None, None
    try:
        task_id = int(tail) if tail.strip() else None
    except ValueError:
        task_id = None
    return command, task_id


__all__ = [
    "COMMANDS",
    "MAX_BODY",
    "command_from_button",
    "command_of",
    "completed_reply",
    "current_reply",
    "error_reply",
    "focus_reply",
    "idle_reply",
    "onboarding_reply",
    "skipped_reply",
]
