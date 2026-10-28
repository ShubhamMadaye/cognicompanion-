"""
CogniCompanion — Timeline Domain Models
=========================================
SQLAlchemy 2.0 ORM models for daily support:
  - medications  (prescriptions + dosage schedule)
  - routines     (recurring daily activities)
  - events       (appointments, outings, visits — timeline entries)
"""

import enum
import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class MedicationFrequency(str, enum.Enum):
    ONCE_DAILY = "ONCE_DAILY"
    TWICE_DAILY = "TWICE_DAILY"
    THREE_TIMES_DAILY = "THREE_TIMES_DAILY"
    FOUR_TIMES_DAILY = "FOUR_TIMES_DAILY"
    WEEKLY = "WEEKLY"
    AS_NEEDED = "AS_NEEDED"


class MedicationTiming(str, enum.Enum):
    BEFORE_BREAKFAST = "BEFORE_BREAKFAST"
    AFTER_BREAKFAST = "AFTER_BREAKFAST"
    BEFORE_LUNCH = "BEFORE_LUNCH"
    AFTER_LUNCH = "AFTER_LUNCH"
    BEFORE_DINNER = "BEFORE_DINNER"
    AFTER_DINNER = "AFTER_DINNER"
    BEDTIME = "BEDTIME"
    SPECIFIC_TIME = "SPECIFIC_TIME"  # Use scheduled_time field


class RoutineCategory(str, enum.Enum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    EXERCISE = "EXERCISE"
    MEAL = "MEAL"
    HYGIENE = "HYGIENE"
    SOCIAL = "SOCIAL"
    COGNITIVE = "COGNITIVE"
    GENERAL = "GENERAL"


class EventType(str, enum.Enum):
    VISIT = "VISIT"             # Family/friend visit
    APPOINTMENT = "APPOINTMENT" # Doctor / hospital
    OUTING = "OUTING"           # Going somewhere
    ACTIVITY = "ACTIVITY"       # Group activity / hobby
    GAME_SESSION = "GAME_SESSION"  # Cognitive game session
    GENERAL = "GENERAL"


# ── medications ───────────────────────────────────────────────────────────────

class Medication(Base):
    """
    Prescriptions the patient takes.

    The PME uses this to safely answer:
      "What medicine do I take after breakfast?"
    with appropriate disclaimers (blueprint Section 8 — Confidence & Safety Layer).
    """
    __tablename__ = "medications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)   # e.g. "500 mg"
    frequency: Mapped[MedicationFrequency] = mapped_column(
        Enum(MedicationFrequency, name="medication_frequency"), nullable=False
    )
    timing: Mapped[MedicationTiming] = mapped_column(
        Enum(MedicationTiming, name="medication_timing"), nullable=False
    )
    scheduled_time: Mapped[time | None] = mapped_column(
        Time, nullable=True
    )  # Used when timing=SPECIFIC_TIME
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    adherence_logs: Mapped[list["MedicationAdherenceLog"]] = relationship(
        "MedicationAdherenceLog", back_populates="medication", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Medication id={self.id} name={self.name!r} patient_id={self.patient_id}>"


class MedicationAdherenceLog(Base):
    """
    Tracks whether a medication was taken at the scheduled time.
    Used by analytics to compute medication_adherence in daily_statistics.
    """
    __tablename__ = "medication_adherence_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    medication_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("medications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    taken: Mapped[bool] = mapped_column(Boolean, nullable=False)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    medication: Mapped[Medication] = relationship("Medication", back_populates="adherence_logs")

    def __repr__(self) -> str:
        return f"<MedicationAdherenceLog medication_id={self.medication_id} date={self.log_date} taken={self.taken}>"


# ── routines ──────────────────────────────────────────────────────────────────

class Routine(Base):
    """
    A recurring daily activity in the patient's schedule.

    Examples: "08:00 Breakfast", "10:00 Walk", "14:00 Rest".
    Drives the daily prompt: "You have [routine] now."
    """
    __tablename__ = "routines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[RoutineCategory] = mapped_column(
        Enum(RoutineCategory, name="routine_category"), nullable=False
    )
    scheduled_time: Mapped[time] = mapped_column(Time, nullable=False)
    # Day-of-week bitmask: Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32, Sun=64
    # Default 127 = every day
    days_of_week: Mapped[int] = mapped_column(Integer, default=127, nullable=False)
    icon_emoji: Mapped[str | None] = mapped_column(String(10), nullable=True)  # e.g. "🍳"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Routine id={self.id} title={self.title!r} time={self.scheduled_time}>"


# ── events ────────────────────────────────────────────────────────────────────

class Event(Base):
    """
    One-off events on the patient's timeline.

    These are distinct from recurring Routines — they represent specific
    appointments, visits, or outings logged by caregivers.
    Also auto-created when a GameSession completes (type=GAME_SESSION).
    """
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    icon_emoji: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Link to a related memory, if any
    linked_memory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memories.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Event id={self.id} type={self.event_type} title={self.title!r}>"
