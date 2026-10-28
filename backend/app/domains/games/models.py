"""
CogniCompanion — Games Domain Models
=======================================
SQLAlchemy 2.0 ORM models for cognitive gaming:
  - games          (game definitions: type, difficulty bounds)
  - game_sessions  (individual play sessions with performance metrics)
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class GameType(str, enum.Enum):
    """The four MVP cognitive games (blueprint Section 4 — MVP 2)."""
    MEMORY_MATCH = "MEMORY_MATCH"         # Card matching game
    SEQUENCE_RECALL = "SEQUENCE_RECALL"   # Reproduce a shown sequence
    PICTURE_RECALL = "PICTURE_RECALL"     # Answer questions about a hidden image
    OBJECT_RECALL = "OBJECT_RECALL"       # Recall a list of shown objects


class DifficultyLevel(str, enum.Enum):
    """
    Discrete difficulty tiers.
    The Adaptive Engine moves between these based on accuracy + reaction time.
    """
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class SessionStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"  # Patient quit mid-session


# ── games ─────────────────────────────────────────────────────────────────────

class Game(Base):
    """
    Game catalogue — one row per game type.

    min_difficulty / max_difficulty and estimated_duration_seconds
    help the Adaptive Engine configure sessions without hardcoding values.
    """
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_type: Mapped[GameType] = mapped_column(
        Enum(GameType, name="game_type"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, name="difficulty_level"),
        default=DifficultyLevel.EASY,
        nullable=False,
    )
    max_difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, name="difficulty_level"),
        default=DifficultyLevel.HARD,
        nullable=False,
    )
    estimated_duration_seconds: Mapped[int] = mapped_column(
        Integer, default=180, nullable=False
    )  # Approximate session length at medium difficulty
    icon_emoji: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Relationships
    sessions: Mapped[list["GameSession"]] = relationship(
        "GameSession", back_populates="game", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Game id={self.id} type={self.game_type}>"


# ── game_sessions ─────────────────────────────────────────────────────────────

class GameSession(Base):
    """
    A single play session of a cognitive game.

    Performance metrics (score, accuracy, reaction_time_ms, mistakes) feed:
      1. The Adaptive Difficulty Engine   → adjust difficulty for next session
      2. Analytics Domain                 → compute CPI components
      3. Caregiver Dashboard              → game performance panel
      4. Timeline                         → auto-creates an Event(GAME_SESSION)

    Adaptive difficulty logic (blueprint Section 7):
      accuracy > 85%  → increase difficulty
      60–85%          → maintain
      < 60%           → reduce difficulty
    """
    __tablename__ = "game_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"),
        default=SessionStatus.IN_PROGRESS,
        nullable=False,
    )
    difficulty_level: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, name="difficulty_level"), nullable=False
    )

    # ── Performance Metrics ──────────────────────────────────────────────────
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)       # Raw score
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)    # 0.0–1.0
    reaction_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Average ms
    mistakes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_items: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Items presented
    correct_items: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Adaptive Engine Output ───────────────────────────────────────────────
    next_difficulty: Mapped[DifficultyLevel | None] = mapped_column(
        Enum(DifficultyLevel, name="difficulty_level"), nullable=True
    )  # Recommended difficulty for the patient's next session of this game

    # ── Timing ───────────────────────────────────────────────────────────────
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    game: Mapped[Game] = relationship("Game", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<GameSession id={self.id} game_id={self.game_id} patient_id={self.patient_id} accuracy={self.accuracy}>"
