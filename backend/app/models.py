"""SQLAlchemy database models for the 1Thing executive core.

Tables:
- ``users``: phone-number identity (Invariant 7: phone OTP only, no passwords).
- ``tasks``: candidate/active/completed work. At most one row per user may
  hold ``status == 'in_progress'`` (Invariant 1), enforced by
  :class:`app.services.state.SingleActiveTaskGuard`.
- ``invariant_logs``: audit trail of every guard intervention.

The engine URL comes from ``DATABASE_URL`` (PostgreSQL 16 in production,
a local SQLite file for development).
"""

import enum
import os
from collections.abc import Iterator
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./onething.db")


class TaskStatus(str, enum.Enum):
    """Lifecycle states for a task.

    - ``in_progress``: the single visible task (Invariant 1).
    - ``queued``: hidden reserve backlog (Invariant 2).
    - ``completed``: done, awaiting the midnight sweep (Invariant 4).
    - ``archived``: swept or explicitly retired.
    """

    IN_PROGRESS = "in_progress"
    QUEUED = "queued"
    COMPLETED = "completed"
    ARCHIVED = "archived"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    tasks: Mapped[list["Task"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    invariant_logs: Mapped[list["InvariantLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    first_micro_step: Mapped[str] = mapped_column(Text, nullable=False, default="")
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    energy_required: Mapped[str] = mapped_column(String(8), nullable=False, default="medium")
    status: Mapped[TaskStatus] = mapped_column(
        Enum(
            TaskStatus,
            native_enum=False,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=TaskStatus.QUEUED,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    last_nudged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    nudge_silenced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship(back_populates="tasks")


class InvariantLog(Base):
    __tablename__ = "invariant_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    invariant: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="invariant_logs")


def get_engine(database_url: str | None = None):
    url = database_url or DATABASE_URL
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(database_url: str | None = None) -> None:
    """Create all tables. Called once at application startup."""
    Base.metadata.create_all(get_engine(database_url))


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_user(db: Session, phone_number: str) -> User:
    """Resolve the WhatsApp sender identity to a User row."""
    user = db.query(User).filter_by(phone_number=phone_number).first()
    if user is None:
        user = User(phone_number=phone_number)
        db.add(user)
        db.flush()
    return user
