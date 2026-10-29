"""Contract tests for the WhatsApp reply templates.

These are pure-formatting tests: no database, no network. They lock the
conversational invariants that the hackathon demo depends on.
"""

from app.services import whatsapp_templates as tpl


def _selected(**overrides):
    task = {
        "id": 7,
        "title": "Draft the Q3 investor update",
        "first_micro_step": "Open the doc and type the subject line",
        "estimated_minutes": 12,
        "energy_required": "low",
    }
    task.update(overrides)
    return task


def test_focus_reply_surfaces_one_task_and_one_step():
    body = tpl.focus_reply(
        {"selected_task": _selected(), "queued_backlog_count": 4},
        dump="email alice, do taxes, call the bank",
    )

    assert "*YOUR ONE THING*" in body
    assert "Draft the Q3 investor update" in body
    assert "*FIRST STEP*" in body
    assert "Open the doc and type the subject line" in body
    assert "12 MIN · LOW" in body


def test_focus_reply_uses_reserve_count_only():
    body = tpl.focus_reply(
        {
            "selected_task": _selected(),
            "queued_backlog_count": 4,
            # A rogue payload must never leak reserve titles.
            "reserve_titles": ["Secret title one", "Secret title two"],
        }
    )

    assert "4 more, parked in the hidden reserve." in body
    assert "hidden reserve" in body
    assert "Secret title" not in body


def test_focus_reply_singular_reserve():
    body = tpl.focus_reply(
        {"selected_task": _selected(), "queued_backlog_count": 1}
    )
    assert "1 more, parked in the hidden reserve." in body
    assert "1 more, parked" in body


def test_focus_reply_whole_list():
    body = tpl.focus_reply(
        {"selected_task": _selected(), "queued_backlog_count": 0}
    )
    assert "whole list" in body


def test_long_dump_is_acknowledged_differently():
    short = tpl.focus_reply(
        {"selected_task": _selected(), "queued_backlog_count": 2}, dump="email alice"
    )
    long = tpl.focus_reply(
        {"selected_task": _selected(), "queued_backlog_count": 2},
        dump="thought " * 60,
    )
    assert "big dump" not in short
    assert "big dump" in long


def test_completed_reply_promotes_next():
    body = tpl.completed_reply(
        {
            "next_task": _selected(title="Reply to the landlord", estimated_minutes=8),
            "queued_backlog_count": 0,
        }
    )
    assert "*DONE.*" in body
    assert "Reply to the landlord" in body
    assert "Nothing else is waiting." in body


def test_completed_reply_clear_surface():
    body = tpl.completed_reply({"next_task": None, "queued_backlog_count": 0})
    assert "last thing on the surface" in body


def test_skipped_reply_parks_without_shame():
    body = tpl.skipped_reply(
        {"next_task": None, "queued_backlog_count": 2, "task": _selected()}
    )
    assert "*SKIPPED.*" in body
    assert "Parked, not deleted." in body
    assert "2 more, parked" in body


def test_skip_of_only_task_names_it_honestly():
    same = _selected()
    body = tpl.skipped_reply(
        {"task": same, "next_task": same, "queued_backlog_count": 1}
    )
    assert "only thing waiting" in body
    assert "smaller first step" in body.lower()


def test_idle_reply_reports_reserve():
    body = tpl.idle_reply(3)
    assert "*STANDBY.*" in body
    assert "3 more, parked in the hidden reserve." in body


def test_command_matching_is_exact():
    assert tpl.command_of(" Done. ") == "DONE"
    assert tpl.command_of("skip!") == "SKIP"
    assert tpl.command_of("done the report finally") is None
    assert tpl.command_of("") is None


def test_body_is_clipped_to_whatsapp_budget():
    body = tpl.focus_reply(
        {
            "selected_task": _selected(
                title="T" * 500,
                first_micro_step="S" * 2000,
            ),
            "queued_backlog_count": 0,
        }
    )
    assert len(body) <= tpl.MAX_BODY


def test_reply_avoids_unstable_whatsapp_markup():
    body = tpl.focus_reply(
        {"selected_task": _selected(), "queued_backlog_count": 2}
    )
    # Italic and arrow glyphs render inconsistently across WhatsApp clients.
    assert "_" not in body
    assert "▸" not in body


def test_onboarding_states_the_contract():
    body = tpl.onboarding_reply()
    assert "*1THING.*" in body
    assert "hidden reserve" in body
    assert "one physical next step" in body.lower()


def test_current_reply_renders_active_task():
    body = tpl.current_reply(_selected(), 3)
    assert "*ON YOUR SURFACE*" in body
    assert "Draft the Q3 investor update" in body
    assert "3 more, parked" in body


def test_current_reply_without_task_is_standby():
    assert "*STANDBY.*" in tpl.current_reply(None, 0)


def test_button_ids_parse_to_command_and_task():
    assert tpl.command_from_button("done:42") == ("DONE", 42)
    assert tpl.command_from_button("skip:7") == ("SKIP", 7)
    assert tpl.command_from_button("done") == ("DONE", None)
    assert tpl.command_from_button("nope:1") == (None, None)
    assert tpl.command_from_button("") == (None, None)
