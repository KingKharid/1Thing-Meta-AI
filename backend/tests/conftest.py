"""Shared fixtures for the 1Thing backend test suite."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, User


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Each test starts with an empty window so counts never leak."""
    from app.services.ratelimit import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(autouse=True)
def _no_live_providers(monkeypatch):
    """Refuse to spend model credits from a test run.

    Both provider seams are stubbed to raise by default. A test that wants
    a model answer patches the seam it cares about, which overrides this.
    Without the guard, a test that forgets one provider silently reaches
    the real API — it passes locally, flakes in CI, and bills the account.
    """
    from app.services import triage as triage_module

    def _blocked(*args, **kwargs):
        raise AssertionError(
            "a test reached a live model provider; patch the seam explicitly"
        )

    monkeypatch.setattr(triage_module, "evaluate_single_task_meta", _blocked)
    monkeypatch.setattr(triage_module, "evaluate_single_task_baseten", _blocked)
    yield


@pytest.fixture()
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def user(db: Session) -> User:
    user = User(phone_number="+15550001111")
    db.add(user)
    db.commit()
    return user
