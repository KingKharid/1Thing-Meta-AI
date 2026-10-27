"""Rhythm tests: time-of-day energy weighting engine."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session
from tests.helpers import backdate, make_task

from app.models import Task, TaskStatus, User
from app.services.rhythm import (
    ENERGY_LEVELS,
    bucket_for,
    learn_energy_profile,
    recommend_energy,
    suggest_context,
)
from app.services.state import SingleActiveTaskGuard


def _complete_at(db: Session, user_id: int, moment: datetime, energy: str) -> Task:
    task = make_task(user_id, f"{energy} work", energy_required=energy)
    db.add(task)
    SingleActiveTaskGuard().activate_task(db, task)
    SingleActiveTaskGuard().set_status(db, task, TaskStatus.COMPLETED)
    return backdate(db, task, completed_at=moment)


@pytest.mark.parametrize(
    ("hour", "expected"),
    [(5, "morning"), (9, "morning"), (11, "morning"), (12, "afternoon"),
     (16, "afternoon"), (17, "evening"), (21, "evening"), (22, "night"),
     (0, "night"), (4, "night")],
)
def test_bucket_boundaries(hour: int, expected: str):
    assert bucket_for(datetime(2026, 1, 5, hour, 30, tzinfo=timezone.utc)) == expected


def test_cold_start_is_uniform_and_recommends_low(db: Session, user: User):
    profile = learn_energy_profile(db, user.id)
    for bucket, weights in profile.items():
        assert set(weights) == set(ENERGY_LEVELS)
        assert sum(weights.values()) == pytest.approx(1.0)
        assert all(w == pytest.approx(1 / 3) for w in weights.values())

    morning = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
    assert recommend_energy(db, user.id, now=morning) == "low"


def test_learning_biases_toward_completed_energy(db: Session, user: User):
    for day in (5, 6, 7):
        _complete_at(
            db, user.id, datetime(2026, 1, day, 9, 0, tzinfo=timezone.utc), "high"
        )
    _complete_at(db, user.id, datetime(2026, 1, 5, 20, 0, tzinfo=timezone.utc), "low")

    profile = learn_energy_profile(db, user.id)
    assert profile["morning"]["high"] > profile["morning"]["medium"]
    assert profile["morning"]["high"] > profile["morning"]["low"]
    assert profile["evening"]["low"] > profile["evening"]["high"]

    morning = datetime(2026, 1, 8, 9, 0, tzinfo=timezone.utc)
    evening = datetime(2026, 1, 8, 20, 0, tzinfo=timezone.utc)
    assert recommend_energy(db, user.id, now=morning) == "high"
    assert recommend_energy(db, user.id, now=evening) == "low"


def test_stale_archives_carry_no_signal(db: Session, user: User):
    stale = make_task(user.id, "Never served", energy_required="high")
    db.add(stale)
    SingleActiveTaskGuard().set_status(db, stale, TaskStatus.ARCHIVED)
    db.commit()

    profile = learn_energy_profile(db, user.id)
    assert all(w == pytest.approx(1 / 3) for w in profile["morning"].values())


def test_suggest_context_matches_pipeline_shape(db: Session, user: User):
    morning = datetime(2026, 1, 8, 9, 0, tzinfo=timezone.utc)
    context = suggest_context(db, user.id, now=morning, available_minutes=45)
    assert context == {"available_minutes": 45, "energy": "low", "time_of_day": "morning"}
