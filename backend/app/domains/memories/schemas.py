"""
CogniCompanion — Memories Domain Schemas
==========================================
Pydantic v2 request/response models for People, Memories, and MemoryMedia.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.domains.memories.models import MediaType, MemoryType, StorageProviderType


# ── Person Schemas ────────────────────────────────────────────────────────────

class CreatePersonRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    relationship: str | None = Field(default=None, max_length=100)
    description: str | None = None


class UpdatePersonRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    relationship: str | None = None
    description: str | None = None
    is_active: bool | None = None


class PersonResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    patient_id: uuid.UUID
    name: str
    relationship: str | None
    description: str | None
    photo_url: str | None
    is_active: bool
    created_at: datetime


# ── Memory Schemas ────────────────────────────────────────────────────────────

class CreateMemoryRequest(BaseModel):
    memory_type: MemoryType
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    location: str | None = Field(default=None, max_length=200)
    event_date: date
    is_significant: bool = False
    person_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="People involved in this memory (optional)."
    )


class UpdateMemoryRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    location: str | None = None
    event_date: date | None = None
    is_significant: bool | None = None
    person_ids: list[uuid.UUID] | None = None


class MemoryMediaResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    media_type: MediaType
    file_url: str
    original_filename: str | None
    mime_type: str | None
    file_size_bytes: int | None
    caption: str | None
    created_at: datetime


class MemoryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    patient_id: uuid.UUID
    memory_type: MemoryType
    title: str
    description: str | None
    location: str | None
    event_date: date
    is_significant: bool
    created_at: datetime
    updated_at: datetime
    media: list[MemoryMediaResponse] = []
    people: list[PersonResponse] = []


class MemoryListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    patient_id: uuid.UUID
    memory_type: MemoryType
    title: str
    event_date: date
    is_significant: bool
    location: str | None
    media_count: int = 0
    created_at: datetime
