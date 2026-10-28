"""
CogniCompanion — Patients Domain Schemas
==========================================
Pydantic v2 request/response models for user and patient management.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.domains.patients.models import PreferredLanguage, UserRole


# ── User Schemas ──────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=8, max_length=100)
    role: UserRole = UserRole.CAREGIVER


# ── Patient Schemas ───────────────────────────────────────────────────────────

class CreatePatientRequest(BaseModel):
    """
    Create a new patient account.
    The caregiver submits this — a user account is created for the patient
    with role=PATIENT, then a patient profile record is linked.
    """
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=8, max_length=100)
    date_of_birth: date | None = None
    preferred_language: PreferredLanguage = PreferredLanguage.ENGLISH
    emergency_contact_name: str | None = Field(default=None, max_length=200)
    emergency_contact_phone: str | None = Field(default=None, max_length=20)
    medical_notes: str | None = None
    # Relationship info for the caregiver_patient link
    caregiver_relationship: str | None = Field(
        default=None, max_length=100, description="e.g. 'daughter', 'nurse'"
    )
    is_primary_caregiver: bool = True


class PatientResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    date_of_birth: date | None
    preferred_language: PreferredLanguage
    profile_photo_url: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    created_at: datetime
    # Nested user info
    user: UserResponse


class PatientListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    preferred_language: PreferredLanguage
    created_at: datetime
    user: UserResponse


class UpdatePatientRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    date_of_birth: date | None = None
    preferred_language: PreferredLanguage | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    medical_notes: str | None = None


# ── CaregiverPatient Schemas ──────────────────────────────────────────────────

class AssignCaregiverRequest(BaseModel):
    caregiver_id: uuid.UUID
    relationship_type: str | None = Field(default=None, max_length=100)
    is_primary: bool = False


class CaregiverAssignmentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    caregiver_id: uuid.UUID
    patient_id: uuid.UUID
    relationship_type: str | None
    is_primary: bool
    assigned_at: datetime


# ── Dashboard Summary Schema ──────────────────────────────────────────────────

class TodaySummaryItem(BaseModel):
    total_medications: int = 0
    taken_medications: int = 0
    pending_medications: int = 0
    total_routines: int = 0
    completed_routines: int = 0
    total_events: int = 0


class CognitiveSummaryItem(BaseModel):
    status: str
    cpi_score: float | None = None
    cpi_delta: float | None = None
    games_completed_today: int = 0
    disclaimer: str


class MemorySummaryItem(BaseModel):
    total_memories: int = 0
    total_people: int = 0
    latest_memory_title: str | None = None
    latest_memory_date: date | None = None


class AttentionSummaryItem(BaseModel):
    pending_medication_names: list[str] = []
    missed_medications: int = 0
    alerts: list[str] = []


class DashboardSummaryResponse(BaseModel):
    patient: PatientResponse
    today: TodaySummaryItem
    cognitive: CognitiveSummaryItem
    memory: MemorySummaryItem
    attention: AttentionSummaryItem
