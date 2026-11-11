"""SQLAlchemy ORM models for QuickPoll surveys and options."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Base ORM declarative model."""


def generate_short_id() -> str:
    """Return an 8-character random hex poll ID."""
    return uuid.uuid4().hex[:8]


class Poll(Base):
    """Survey entity containing voteable choices."""

    __tablename__ = "polls"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_short_id)
    question: Mapped[str] = mapped_column(String(300), nullable=False)
    allow_multiple: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now_naive)

    options: Mapped[list[PollOption]] = relationship(
        "PollOption", back_populates="poll", cascade="all, delete-orphan"
    )


class PollOption(Base):
    """Individual poll choice with atomic counter."""

    __tablename__ = "poll_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    poll_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("polls.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(String(200), nullable=False)
    vote_count: Mapped[int] = mapped_column(Integer, default=0)

    poll: Mapped[Poll] = relationship("Poll", back_populates="options")
