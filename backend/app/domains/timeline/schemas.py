"""
CogniCompanion — Timeline Domain Schemas
==========================================
Pydantic v2 models for Medications, MedicationAdherenceLogs,
Routines, Events, and the combined Timeline view.
"""

import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field

from app.domains.timeline.models import (
    EventType,
    MedicationFrequency,
    MedicationTiming,
    RoutineCategory,
)


# ── Medication Schemas ────────────────────────────────────────────────────────

class CreateMedicationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    dosage: str | None = Field(default=None, max_length=100)
    frequency: MedicationFrequency
    timing: MedicationTiming
    scheduled_time: time | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None


class UpdateMedicationRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    dosage: str | None = None
    frequency: MedicationFrequency | None = None
    timing: MedicationTiming | None = None
    scheduled_time: time | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None
    is_active: bool | None = None


class MedicationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    patient_id: uuid.UUID
    name: str
    dosage: str | None
    frequency: MedicationFrequency
    timing: MedicationTiming
    scheduled_time: time | None
    start_date: date | None
    end_date: date | None
    notes: str | None
    is_active: bool
    created_at: datetime


class LogMedicationRequest(BaseModel):
    log_date: date
    taken: bool
    taken_at: datetime | None = None
    notes: str | None = None


class AdherenceLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    medication_id: uuid.UUID
    log_date: date
    taken: bool
    taken_at: datetime | None
    notes: str | None
    created_at: datetime


# ── Routine Schemas ───────────────────────────────────────────────────────────

class CreateRoutineRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: RoutineCategory
    scheduled_time: time
    days_of_week: int = Field(
        default=127,
        ge=1,
        le=127,
        description="Bitmask: Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32, Sun=64. 127=every day.",
    )
    icon_emoji: str | None = Field(default=None, max_length=10)


class UpdateRoutineRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: RoutineCategory | None = None
    scheduled_time: time | None = None
    days_of_week: int | None = Field(default=None, ge=1, le=127)
    icon_emoji: str | None = None
    is_active: bool | None = None


class RoutineResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    patient_id: uuid.UUID
    title: str
    description: str | None
    category: RoutineCategory
    scheduled_time: time
    days_of_week: int
    icon_emoji: str | None
    is_active: bool
    created_at: datetime


# ── Event Schemas ─────────────────────────────────────────────────────────────

class CreateEventRequest(BaseModel):
    event_type: EventType
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    location: str | None = Field(default=None, max_length=200)
    start_time: datetime
    end_time: datetime | None = None
    icon_emoji: str | None = Field(default=None, max_length=10)
    linked_memory_id: uuid.UUID | None = None


class UpdateEventRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    location: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    icon_emoji: str | None = None


class EventResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    patient_id: uuid.UUID
    event_type: EventType
    title: str
    description: str | None
    location: str | None
    start_time: datetime
    end_time: datetime | None
    icon_emoji: str | None
    linked_memory_id: uuid.UUID | None
    created_at: datetime


# ── Combined Timeline View ─────────────────────────────────────────────────────

class TimelineEntryResponse(BaseModel):
    """
    A single item in the unified timeline view.
    The `kind` field discriminates between entry types for the Flutter UI.
    """
    kind: Literal["routine", "medication", "event", "memory"]
    id: uuid.UUID
    title: str
    description: str | None = None
    icon_emoji: str | None = None
    timestamp: datetime        # Used for chronological sort
    display_time: str          # Human-readable e.g. "08:00"
    metadata: dict = Field(default_factory=dict)  # Type-specific extra fields
