"""
CogniCompanion — Memories Domain Models
=========================================
SQLAlchemy 2.0 ORM models for the Personalized Memory Engine (PME):
  - people        (known persons in the patient's life)
  - memories      (structured events / facts)
  - memory_media  (photos, audio attached to memories)
"""

import enum
import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domains.voice.models import MemoryEmbedding

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class MemoryType(str, enum.Enum):
    """
    Categorises memories for retrieval and display.

    Used by the Intent Detector to route queries to the right retriever.
    """
    VISIT = "VISIT"             # Someone visited the patient
    OUTING = "OUTING"           # Patient went somewhere
    MEAL = "MEAL"               # Meal event
    MEDICATION = "MEDICATION"   # Medication taken / administered
    APPOINTMENT = "APPOINTMENT" # Doctor / specialist appointment
    FAMILY_STORY = "FAMILY_STORY"  # Personal narrative / anecdote
    GENERAL = "GENERAL"         # Anything else


class MediaType(str, enum.Enum):
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"


class StorageProviderType(str, enum.Enum):
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"


# ── people ─────────────────────────────────────────────────────────────────────

class Person(Base):
    """
    A person known to the patient — family, friends, care staff.

    The PME uses this to answer:
      "Who visited me yesterday?"   → "Rahul — your son."
      "Tell me about Priya."        → uses description field
    """
    __tablename__ = "people"

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
    relationship: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g. "daughter", "doctor", "neighbour"
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Rich text the caregiver writes about this person
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
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
    memories: Mapped[list["Memory"]] = orm_relationship(
        "Memory",
        secondary="memory_person",
        back_populates="people",
    )

    def __repr__(self) -> str:
        return f"<Person id={self.id} name={self.name!r} patient_id={self.patient_id}>"


# ── memories ──────────────────────────────────────────────────────────────────

class Memory(Base):
    """
    A structured memory event in the patient's life.

    Supports:
      - Structured retrieval (event_date, memory_type, location)
      - Semantic retrieval (description embedded via pgvector)
      - Linked media (photos, audio)
      - Linked people (who was involved)

    created_by references the User (caregiver / admin) who logged the memory.
    """
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    memory_type: Mapped[MemoryType] = mapped_column(
        Enum(MemoryType, name="memory_type"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Natural language description — this is what gets embedded
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_significant: Mapped[bool] = mapped_column(
        default=False, nullable=False
    )  # Pinned important memories the PME should always surface
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
    media: Mapped[list["MemoryMedia"]] = orm_relationship(
        "MemoryMedia", back_populates="memory", cascade="all, delete-orphan"
    )
    people: Mapped[list[Person]] = orm_relationship(
        "Person",
        secondary="memory_person",
        back_populates="memories",
    )
    embedding: Mapped["MemoryEmbedding | None"] = orm_relationship(
        "app.domains.voice.models.MemoryEmbedding",
        back_populates="memory",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Memory id={self.id} title={self.title!r} date={self.event_date}>"


# ── memory_person (association table) ────────────────────────────────────────

from sqlalchemy import Table, Column

memory_person = Table(
    "memory_person",
    Base.metadata,
    Column("memory_id", UUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True),
    Column("person_id", UUID(as_uuid=True), ForeignKey("people.id", ondelete="CASCADE"), primary_key=True),
)


# ── memory_media ──────────────────────────────────────────────────────────────

class MemoryMedia(Base):
    """
    Files (images, audio clips) attached to a memory.

    Storage metadata is kept here so switching providers (local → S3)
    only requires updating storage_provider and file_url — no schema change.
    """
    __tablename__ = "memory_media"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="media_type"), nullable=False
    )
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. "image/jpeg"
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    storage_provider: Mapped[StorageProviderType] = mapped_column(
        Enum(StorageProviderType, name="storage_provider_type"),
        default=StorageProviderType.LOCAL,
        nullable=False,
    )
    checksum_sha256: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # For integrity verification
    caption: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    memory: Mapped[Memory] = orm_relationship("Memory", back_populates="media")

    def __repr__(self) -> str:
        return f"<MemoryMedia id={self.id} type={self.media_type} memory_id={self.memory_id}>"
