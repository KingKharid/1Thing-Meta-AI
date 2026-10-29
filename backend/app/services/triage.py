"""Dump → the one physical next step, plus the reserve behind it.

Every capture surface files raw text. Turning that text into something a
person can actually start — a short title, an exact first move, a time
and energy estimate — is the model's job, and this module is the only
place that asks for it. Web, WhatsApp and any later surface share the
same contract so they cannot drift apart.

A dump is not a task. People empty a week of loose ends into one message,
so :func:`extract` returns *every* distinct thing the model found, in the
order it says they should happen. The caller surfaces the first one and
hides the rest in the reserve, which is the whole product: the mountain
is captured, never displayed.

Failure is explicit. :func:`extract` returns an empty list and the caller
keeps the raw dump with an empty step. An invented step would be worse
than no step — the product's entire promise is that the step on screen is
real.
"""

from __future__ import annotations

import logging
import re

from app.meta_client import evaluate_single_task_baseten, evaluate_single_task_meta

log = logging.getLogger(__name__)

MAX_TITLE_CHARS = 120
MAX_STEP_CHARS = 160
ENERGY_LEVELS = ("low", "medium", "high")

# One dump is one sitting's worth of capture. Twenty is already more than
# a person can hold in mind; beyond that the reserve stops being a
# courtesy and starts being another mountain.
MAX_TASKS_PER_DUMP = 20


def _clean(value: object, limit: int) -> str:
    return str(value or "").strip()[:limit].strip()


def _normalise_one(item: object) -> dict | None:
    """Accept one task only if it carries a usable step.

    Guards against the three ways an entry can look successful and still be
    useless: not an object, an empty step, or a step that merely restates
    the title.
    """
    if not isinstance(item, dict):
        return None

    title = _clean(item.get("title"), MAX_TITLE_CHARS)
    step = _clean(item.get("first_micro_step"), MAX_STEP_CHARS)
    if not step:
        return None
    if title and step.casefold() == title.casefold():
        return None
    if not title:
        # Without a title the reserve would show a nameless row later.
        return None

    try:
        minutes = int(item.get("estimated_minutes"))
    except (TypeError, ValueError):
        minutes = 15
    energy = item.get("energy_required")
    if energy not in ENERGY_LEVELS:
        energy = "medium"

    return {
        "title": title,
        "first_micro_step": step,
        "estimated_minutes": minutes if minutes > 0 else 15,
        "energy_required": energy,
    }


def _normalise(result: object, limit: int = MAX_TASKS_PER_DUMP) -> list[dict]:
    """Turn a model reply into an ordered, deduplicated list of tasks.

    Accepts the current ``{"tasks": [...]}`` shape and the older
    ``{"selected_task": {...}}`` shape, so a provider still serving the
    previous prompt cannot silently drop a dump.

    Order is preserved: the model decides what the user sees first, and
    the caller relies on that decision rather than re-sorting.
    """
    if not isinstance(result, dict):
        return []

    raw_items = result.get("tasks")
    if not isinstance(raw_items, list):
        selected = result.get("selected_task")
        raw_items = [selected] if isinstance(selected, dict) else []

    tasks: list[dict] = []
    seen: set[str] = set()
    for item in raw_items:
        normalised = _normalise_one(item)
        if normalised is None:
            continue
        key = normalised["title"].casefold()
        if key in seen:
            continue
        seen.add(key)
        tasks.append(normalised)
        if len(tasks) >= limit:
            break

    return tasks


def extract(
    raw_dump: str,
    context: dict,
    engine: str = "meta",
    limit: int = MAX_TASKS_PER_DUMP,
) -> list[dict]:
    """Ask the model what is actually in this dump, in priority order.

    Tries the requested engine, then the other configured provider, so a
    single provider outage does not leave the surface empty. Every failure
    mode — transport, timeout, malformed JSON, no usable step — yields an
    empty list rather than a fabricated action.
    """
    raw_dump = (raw_dump or "").strip()
    if not raw_dump:
        return []

    order = ("baseten", "meta") if engine == "baseten" else ("meta", "baseten")
    for name in order:
        try:
            reply = (
                evaluate_single_task_baseten(raw_dump, context)
                if name == "baseten"
                else evaluate_single_task_meta(raw_dump, context)
            )
        except Exception as exc:  # noqa: BLE001 - any provider failure is recoverable
            log.warning("triage via %s failed: %s", name, exc)
            continue

        tasks = _normalise(reply, limit=limit)
        if tasks:
            return tasks
        log.warning("triage via %s returned no usable task", name)

    return []


def triage(raw_dump: str, context: dict, engine: str = "meta") -> dict | None:
    """The one task to show right now, or ``None``.

    A thin wrapper for callers that only need the head of the queue —
    WhatsApp's reply, and deriving a step for an existing row.
    """
    tasks = extract(raw_dump, context, engine=engine, limit=1)
    return tasks[0] if tasks else None


# ------------------------------------------------------- heuristic fallback

BULLET_PREFIX = re.compile(r"^\s*(?:[-*•>]|\d+[.)])\s+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_LOW_ENERGY_WORDS = ("read", "watch", "tidy", "file", "sort", "water", "rest")
_HIGH_ENERGY_WORDS = (
    "call",
    "meet",
    "write",
    "build",
    "fix",
    "ship",
    "tax",
    "present",
    "negotiat",
)


def _minutes_for(chunk: str) -> int:
    if len(chunk) < 40:
        return 5
    if len(chunk) < 120:
        return 15
    return 25


def _energy_for(chunk: str) -> str:
    lowered = chunk.casefold()
    if any(word in lowered for word in _HIGH_ENERGY_WORDS):
        return "high"
    if any(word in lowered for word in _LOW_ENERGY_WORDS):
        return "low"
    return "medium"


def _chunks(raw_dump: str) -> list[str]:
    text = (raw_dump or "").strip()
    if not text:
        return []
    chunks: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        lines = [BULLET_PREFIX.sub("", line).strip() for line in para.splitlines()]
        chunks.extend(line for line in lines if line)
    if len(chunks) <= 1:
        # One wall of text: split sentences so a week of loose ends
        # still files as discrete tasks.
        sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
        if len(sentences) > 1:
            return sentences
    return chunks


def fallback(raw_dump: str, limit: int = MAX_TASKS_PER_DUMP) -> list[dict]:
    """Deterministic last resort: the user's own words, verbatim.

    Runs only when every model provider failed. Nothing is invented and
    nothing is dropped: each chunk becomes a task titled with its head
    while the FULL chunk is kept as the step, so a provider outage can
    never silently eat a week of thoughts. Minutes and energy are
    length/keyword estimates — honestly approximate, always revisable
    through the derive endpoint once the model is back.
    """
    tasks: list[dict] = []
    seen: set[str] = set()
    for chunk in _chunks(raw_dump):
        title = _clean(chunk, MAX_TITLE_CHARS)
        if not title:
            continue
        key = title.casefold()
        if key in seen:
            continue
        seen.add(key)
        tasks.append(
            {
                "title": title,
                "first_micro_step": chunk.strip(),
                "estimated_minutes": _minutes_for(chunk),
                "energy_required": _energy_for(chunk),
            }
        )
        if len(tasks) >= limit:
            break
    return tasks


def extract_or_fallback(
    raw_dump: str,
    context: dict,
    engine: str = "meta",
    limit: int = MAX_TASKS_PER_DUMP,
) -> tuple[list[dict], bool]:
    """AI extraction with verbatim heuristic fallback.

    Returns ``(tasks, used_fallback)``. Dump-ingestion callers (the
    capture endpoint, the WhatsApp pipeline) use this so a provider
    outage files the user's own words instead of losing the week. The
    derive endpoint deliberately keeps strict :func:`triage` — a step
    derived later must be real, never a restatement.
    """
    tasks = extract(raw_dump, context, engine=engine, limit=limit)
    if tasks:
        return tasks, False
    return fallback(raw_dump, limit=limit), True
