"""
CogniCompanion — Patients Domain Models
=========================================
SQLAlchemy 2.0 ORM models for:
  - users           (all roles)
  - patients        (extended profile for PATIENT users)
  - caregiver_patient (M2M relationship with metadata)
"""

import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    """Role-based access control roles."""
    PATIENT = "PATIENT"
    CAREGIVER = "CAREGIVER"
    DOCTOR = "DOCTOR"
    ADMIN = "ADMIN"


class PreferredLanguage(str, enum.Enum):
    """Supported languages in MVP and near-future scope."""
    ENGLISH = "en"
    HINDI = "hi"
    ASSAMESE = "as"
    BENGALI = "bn"
    MANIPURI = "mni"


# ── users ─────────────────────────────────────────────────────────────────────

class User(Base):
    """
    Central identity table for all roles.

    token_version:
        Incremented on password change or forced logout.
        JWT claims carry a matching `tv` claim — mismatch = rejected token.
        This avoids maintaining a token blacklist.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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
    patient_profile: Mapped["Patient | None"] = relationship(
        "Patient", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    caregiver_assignments: Mapped[list["CaregiverPatient"]] = relationship(
        "CaregiverPatient",
        foreign_keys="CaregiverPatient.caregiver_id",
        back_populates="caregiver",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"


# ── patients ──────────────────────────────────────────────────────────────────

class Patient(Base):
    """
    Extended profile for users with role=PATIENT.

    Stores dementia-care-specific attributes:
      - date_of_birth     → age-appropriate UI/game difficulty defaults
      - preferred_language → drives STT/TTS language selection
      - emergency_contact → for caregiver alert escalation
    """
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    preferred_language: Mapped[PreferredLanguage] = mapped_column(
        Enum(
            PreferredLanguage,
            name="preferred_language",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=PreferredLanguage.ENGLISH,
        nullable=False,
    )
    profile_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    medical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    user: Mapped[User] = relationship("User", back_populates="patient_profile")
    caregiver_assignments: Mapped[list["CaregiverPatient"]] = relationship(
        "CaregiverPatient",
        foreign_keys="CaregiverPatient.patient_id",
        back_populates="patient",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Patient id={self.id} user_id={self.user_id}>"


# ── caregiver_patient ────────────────────────────────────────────────────────

class CaregiverPatient(Base):
    """
    Many-to-many relationship between caregivers (Users) and patients.

    Authorization rule:
        A caregiver may only access data for patients in this table.
        is_primary: True if this is the primary caregiver (receives all alerts).
    """
    __tablename__ = "caregiver_patient"
    __table_args__ = (
        UniqueConstraint("caregiver_id", "patient_id", name="uq_caregiver_patient"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g. "daughter", "son", "nurse"
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    caregiver: Mapped[User] = relationship(
        "User", foreign_keys=[caregiver_id], back_populates="caregiver_assignments"
    )
    patient: Mapped[Patient] = relationship(
        "Patient", foreign_keys=[patient_id], back_populates="caregiver_assignments"
    )

    def __repr__(self) -> str:
        return f"<CaregiverPatient caregiver={self.caregiver_id} patient={self.patient_id}>"
