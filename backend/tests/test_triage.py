"""Triage contract: what counts as a usable model reply.

The whole point of these tests is the negative space — a reply that looks
successful but carries no real step must be rejected, so no surface can
render an invented or meaningless action.

The second half covers a dump: one message can carry a week of loose ends,
and the model's ordering is the product's only priority signal.
"""

import pytest

from app.services import triage as triage_module
from app.services.triage import (
    MAX_TASKS_PER_DUMP,
    _normalise,
    extract,
    extract_or_fallback,
    fallback,
    triage,
)

CONTEXT = {"available_minutes": 25, "energy": "medium", "time_of_day": "morning"}


def _task(**overrides):
    item = {
        "title": "Go to church",
        "first_micro_step": "Put on shoes and grab keys",
        "estimated_minutes": 20,
        "energy_required": "medium",
    }
    item.update(overrides)
    return item


def _reply(**overrides):
    return {"tasks": [_task(**overrides)]}


def _legacy_reply(**overrides):
    return {"selected_task": _task(**overrides), "queued_backlog_count": 0}


# --------------------------------------------------------------- one entry


def test_valid_reply_is_normalised():
    assert _normalise(_reply()) == [
        {
            "title": "Go to church",
            "first_micro_step": "Put on shoes and grab keys",
            "estimated_minutes": 20,
            "energy_required": "medium",
        }
    ]


def test_legacy_selected_task_shape_still_works():
    """A provider still serving the old prompt must not drop the dump."""
    assert _normalise(_legacy_reply()) == _normalise(_reply())


@pytest.mark.parametrize(
    "reply",
    [
        None,
        {},
        {"tasks": None},
        {"tasks": []},
        {"selected_task": None},
        {"selected_task": {}},
        _reply(first_micro_step=""),
        _reply(first_micro_step="   "),
        _reply(title=""),
    ],
)
def test_replies_without_a_usable_task_are_rejected(reply):
    assert _normalise(reply) == []


def test_a_step_that_restates_the_title_is_rejected():
    assert _normalise(_reply(first_micro_step="go to church")) == []


def test_bad_minutes_and_energy_fall_back():
    out = _normalise(_reply(estimated_minutes="soon", energy_required="cosmic"))
    assert out[0]["estimated_minutes"] == 15
    assert out[0]["energy_required"] == "medium"
    assert out[0]["first_micro_step"] == "Put on shoes and grab keys"


# ------------------------------------------------------------------ a dump


def test_order_is_preserved_because_the_model_decides_priority():
    reply = {
        "tasks": [
            _task(title="Send the deposit", first_micro_step="Open the bank app"),
            _task(title="Book the venue", first_micro_step="Call the hall"),
            _task(title="Email Sam", first_micro_step="Open your inbox"),
        ]
    }
    assert [t["title"] for t in _normalise(reply)] == [
        "Send the deposit",
        "Book the venue",
        "Email Sam",
    ]


def test_duplicate_titles_are_collapsed_keeping_the_first():
    reply = {
        "tasks": [
            _task(title="Call the dentist", first_micro_step="Open contacts"),
            _task(title="call the dentist", first_micro_step="Dial the number"),
        ]
    }
    out = _normalise(reply)
    assert len(out) == 1
    assert out[0]["first_micro_step"] == "Open contacts"


def test_one_unusable_entry_does_not_discard_the_rest():
    reply = {
        "tasks": [
            _task(title="Broken", first_micro_step=""),
            _task(title="Fine", first_micro_step="Open the app"),
        ]
    }
    assert [t["title"] for t in _normalise(reply)] == ["Fine"]


def test_the_dump_is_capped():
    reply = {
        "tasks": [
            _task(title=f"Task {i}", first_micro_step=f"Start step {i}")
            for i in range(MAX_TASKS_PER_DUMP + 5)
        ]
    }
    assert len(_normalise(reply)) == MAX_TASKS_PER_DUMP


def test_limit_argument_is_honoured():
    reply = {
        "tasks": [
            _task(title=f"Task {i}", first_micro_step=f"Start step {i}")
            for i in range(5)
        ]
    }
    assert len(_normalise(reply, limit=2)) == 2


# ---------------------------------------------------------------- providers


def test_triage_falls_back_to_the_second_provider(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("meta is down")

    monkeypatch.setattr(triage_module, "evaluate_single_task_meta", boom)
    monkeypatch.setattr(
        triage_module, "evaluate_single_task_baseten", lambda *a, **k: _reply()
    )

    assert triage("going to church", CONTEXT)["first_micro_step"] == (
        "Put on shoes and grab keys"
    )


def test_triage_returns_none_when_every_provider_fails(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr(triage_module, "evaluate_single_task_meta", boom)
    monkeypatch.setattr(triage_module, "evaluate_single_task_baseten", boom)

    assert triage("going to church", CONTEXT) is None


def test_triage_returns_none_for_an_empty_dump(monkeypatch):
    monkeypatch.setattr(
        triage_module,
        "evaluate_single_task_meta",
        lambda *a, **k: pytest.fail("must not call a provider for an empty dump"),
    )

    assert triage("   ", CONTEXT) is None


def test_extract_returns_the_whole_list(monkeypatch):
    reply = {
        "tasks": [
            _task(title="First", first_micro_step="Open A"),
            _task(title="Second", first_micro_step="Open B"),
        ]
    }
    monkeypatch.setattr(
        triage_module, "evaluate_single_task_meta", lambda *a, **k: reply
    )

    assert [t["title"] for t in extract("a week of thoughts", CONTEXT)] == [
        "First",
        "Second",
    ]


def test_extract_is_empty_when_the_provider_returns_nothing(monkeypatch):
    monkeypatch.setattr(
        triage_module, "evaluate_single_task_meta", lambda *a, **k: {"tasks": []}
    )
    monkeypatch.setattr(
        triage_module, "evaluate_single_task_baseten", lambda *a, **k: {"tasks": []}
    )

    assert extract("a week of thoughts", CONTEXT) == []


def test_extract_falls_back_when_the_first_reply_is_unusable(monkeypatch):
    monkeypatch.setattr(
        triage_module, "evaluate_single_task_meta", lambda *a, **k: {"tasks": []}
    )
    monkeypatch.setattr(
        triage_module, "evaluate_single_task_baseten", lambda *a, **k: _reply()
    )

    assert extract("a week of thoughts", CONTEXT)[0]["title"] == "Go to church"


# ------------------------------------------------------- heuristic fallback


def test_fallback_splits_paragraphs_and_strips_bullets():
    dump = "- Call the dentist\n\nWater the plants\n\n1. File the receipts"
    out = fallback(dump)
    assert [t["title"] for t in out] == [
        "Call the dentist",
        "Water the plants",
        "File the receipts",
    ]


def test_fallback_keeps_the_full_chunk_as_the_step():
    long = " ".join(["Email the landlord about the leak"] * 20)
    assert len(long) > 120
    out = fallback(long)
    assert len(out) == 1
    assert out[0]["first_micro_step"] == long  # lossless
    assert len(out[0]["title"]) <= 120  # display-bounded head only


def test_fallback_wall_of_text_splits_sentences():
    out = fallback("Call the bank. Then water the plants! And rest a little.")
    assert len(out) == 3


def test_fallback_dedupes_repeats():
    out = fallback("Call the bank\n\ncall the BANK")
    assert [t["title"] for t in out] == ["Call the bank"]


def test_fallback_estimates_minutes_and_energy():
    call = fallback("Call the bank about the fee")[0]
    assert call["energy_required"] == "high"
    assert call["estimated_minutes"] == 5
    read = fallback("Read the article about sleep")[0]
    assert read["energy_required"] == "low"


def test_fallback_is_capped_like_the_model_path():
    dump = "\n\n".join(f"Thought number {i} to handle" for i in range(30))
    assert len(fallback(dump)) == MAX_TASKS_PER_DUMP


def test_fallback_empty_for_blank():
    assert fallback("   ") == []
    assert fallback("") == []


def test_extract_or_fallback_prefers_the_model(monkeypatch):
    monkeypatch.setattr(
        triage_module, "evaluate_single_task_meta", lambda *a, **k: _reply()
    )
    tasks, used_fallback = extract_or_fallback("going to church", CONTEXT)
    assert used_fallback is False
    assert tasks[0]["title"] == "Go to church"


def test_extract_or_fallback_files_verbatim_when_providers_fail(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr(triage_module, "evaluate_single_task_meta", boom)
    monkeypatch.setattr(triage_module, "evaluate_single_task_baseten", boom)

    tasks, used_fallback = extract_or_fallback(
        "Call the dentist\n\nWater the plants", CONTEXT
    )
    assert used_fallback is True
    assert [t["title"] for t in tasks] == ["Call the dentist", "Water the plants"]
