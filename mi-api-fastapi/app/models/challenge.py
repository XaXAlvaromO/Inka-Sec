"""Retos (escenarios cortos) y sus intentos."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.models import utcnow


class Challenge(Base):
    __tablename__ = "challenges"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    topic: Mapped[str] = mapped_column(String(100), index=True)
    scenario: Mapped[str] = mapped_column(Text)
    # quick = una decisión; steps = escenario por pasos; signals = encuentra las señales.
    kind: Mapped[str] = mapped_column(String(20), default="quick", server_default="quick")
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # pasos o fragmentos (steps / signals)
    options: Mapped[list] = mapped_column(JSON)            # ["opción A", "opción B", ...] (solo quick)
    correct_index: Mapped[int] = mapped_column(Integer)    # nunca se envía al trabajador antes de responder
    feedback: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)  # draft | published | archived
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ChallengeAttempt(Base):
    """Una fila por trabajador y reto. Los retos entrenan: se pueden repetir sin límite.

    selected_index / is_correct guardan el PRIMER intento (lo que la persona sabía antes de practicar);
    last_correct / last_score / tries reflejan la práctica posterior y solo los ve el propio trabajador.
    """
    __tablename__ = "challenge_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)
    selected_index: Mapped[int] = mapped_column(Integer)
    is_correct: Mapped[bool] = mapped_column(Boolean, index=True)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    tries: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    last_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "challenge_id", name="uq_attempt_user_challenge"),)
