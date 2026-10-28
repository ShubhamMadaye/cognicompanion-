"""
CogniCompanion — Memories Router
===================================
Endpoints for People, Memories, and Media.

All routes are scoped to a patient_id verified by verify_caregiver_patient_access.
Patients can also read their own memories (read-only).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import (
    get_current_caregiver,
    get_current_user,
    verify_caregiver_patient_access,
    verify_patient_self_or_caregiver_access,
)
from app.domains.memories.models import MediaType, MemoryType
from app.domains.memories.schemas import (
    CreateMemoryRequest,
    CreatePersonRequest,
    MemoryListResponse,
    MemoryMediaResponse,
    MemoryResponse,
    PersonResponse,
    UpdateMemoryRequest,
    UpdatePersonRequest,
)
from app.domains.memories.service import MemoryService, PeopleService
from app.domains.patients.models import User, UserRole

router = APIRouter(tags=["Memories"])


# ─────────────────────────────────────────────────────────────────────────────
# PEOPLE
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/patients/{patient_id}/people",
    response_model=PersonResponse,
    status_code=201,
    summary="Add a person to patient's world",
)
async def create_person(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    body: CreatePersonRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _caregiver: Annotated[User, Depends(get_current_caregiver)],
) -> PersonResponse:
    """Add a person (family member, friend, care staff) known to the patient."""
    service = PeopleService(db)
    person = await service.create_person(patient_id, body)
    return PersonResponse.model_validate(person)


@router.get(
    "/patients/{patient_id}/people",
    response_model=list[PersonResponse],
    summary="List people known to the patient",
)
async def list_people(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PersonResponse]:
    service = PeopleService(db)
    people = await service.list_people(patient_id)
    return [PersonResponse.model_validate(p) for p in people]


@router.get(
    "/patients/{patient_id}/people/{person_id}",
    response_model=PersonResponse,
    summary="Get a specific person",
)
async def get_person(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    person_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PersonResponse:
    service = PeopleService(db)
    person = await service.get_person(patient_id, person_id)
    return PersonResponse.model_validate(person)


@router.patch(
    "/patients/{patient_id}/people/{person_id}",
    response_model=PersonResponse,
    summary="Update a person",
)
async def update_person(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    person_id: uuid.UUID,
    body: UpdatePersonRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _caregiver: Annotated[User, Depends(get_current_caregiver)],
) -> PersonResponse:
    service = PeopleService(db)
    person = await service.update_person(patient_id, person_id, body)
    return PersonResponse.model_validate(person)


@router.post(
    "/patients/{patient_id}/people/{person_id}/photo",
    response_model=PersonResponse,
    summary="Upload a photo for a person",
)
async def upload_person_photo(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    person_id: uuid.UUID,
    file: Annotated[UploadFile, File(description="Person photo (JPEG, PNG, WebP)")],
    db: Annotated[AsyncSession, Depends(get_db)],
    _caregiver: Annotated[User, Depends(get_current_caregiver)],
) -> PersonResponse:
    file_bytes = await file.read()
    service = PeopleService(db)
    person = await service.upload_person_photo(
        patient_id, person_id, file_bytes, file.filename or "photo.jpg"
    )
    return PersonResponse.model_validate(person)


# ─────────────────────────────────────────────────────────────────────────────
# MEMORIES
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/patients/{patient_id}/memories",
    response_model=MemoryResponse,
    status_code=201,
    summary="Create a memory",
)
async def create_memory(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    body: CreateMemoryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MemoryResponse:
    """
    Create a new memory for the patient.

    Triggers:
    - Embedding generation (Phase 4)
    - Timeline event creation
    """
    service = MemoryService(db)
    memory = await service.create_memory(patient_id, body, current_user)
    return MemoryResponse.model_validate(memory)


@router.get(
    "/patients/{patient_id}/memories",
    response_model=list[MemoryListResponse],
    summary="List memories",
)
async def list_memories(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    memory_type: MemoryType | None = Query(default=None),
    start_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    significant_only: bool = Query(default=False),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[MemoryListResponse]:
    """List memories with optional filters. Returns newest first."""
    from datetime import date as date_type
    service = MemoryService(db)
    memories = await service.list_memories(
        patient_id=patient_id,
        memory_type=memory_type.value if memory_type else None,
        start_date=date_type.fromisoformat(start_date) if start_date else None,
        end_date=date_type.fromisoformat(end_date) if end_date else None,
        significant_only=significant_only,
        limit=limit,
        offset=offset,
    )

    results = []
    for m in memories:
        item = MemoryListResponse.model_validate(m)
        item.media_count = len(m.media)
        results.append(item)
    return results


@router.get(
    "/patients/{patient_id}/memories/{memory_id}",
    response_model=MemoryResponse,
    summary="Get a memory with full details",
)
async def get_memory(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    memory_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MemoryResponse:
    service = MemoryService(db)
    memory = await service.get_memory(patient_id, memory_id)
    return MemoryResponse.model_validate(memory)


@router.patch(
    "/patients/{patient_id}/memories/{memory_id}",
    response_model=MemoryResponse,
    summary="Update a memory",
)
async def update_memory(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    memory_id: uuid.UUID,
    body: UpdateMemoryRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _caregiver: Annotated[User, Depends(get_current_caregiver)],
) -> MemoryResponse:
    service = MemoryService(db)
    memory = await service.update_memory(patient_id, memory_id, body)
    return MemoryResponse.model_validate(memory)


@router.delete(
    "/patients/{patient_id}/memories/{memory_id}",
    status_code=204,
    summary="Delete a memory",
)
async def delete_memory(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    memory_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _caregiver: Annotated[User, Depends(get_current_caregiver)],
) -> None:
    service = MemoryService(db)
    await service.delete_memory(patient_id, memory_id)


# ─────────────────────────────────────────────────────────────────────────────
# MEDIA
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/patients/{patient_id}/memories/{memory_id}/media",
    response_model=MemoryMediaResponse,
    status_code=201,
    summary="Upload media (photo / audio) for a memory",
)
async def upload_memory_media(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    memory_id: uuid.UUID,
    file: Annotated[UploadFile, File()],
    db: Annotated[AsyncSession, Depends(get_db)],
    _caregiver: Annotated[User, Depends(get_current_caregiver)],
    caption: str | None = Form(default=None),
) -> MemoryMediaResponse:
    """Attach a photo, audio clip, or video to a memory."""
    file_bytes = await file.read()
    mime = file.content_type or "application/octet-stream"

    # Determine media type from MIME
    if mime.startswith("image/"):
        media_type = MediaType.IMAGE
    elif mime.startswith("audio/"):
        media_type = MediaType.AUDIO
    elif mime.startswith("video/"):
        media_type = MediaType.VIDEO
    else:
        media_type = MediaType.DOCUMENT

    service = MemoryService(db)
    media = await service.attach_media(
        patient_id=patient_id,
        memory_id=memory_id,
        file_bytes=file_bytes,
        filename=file.filename or "upload",
        mime_type=mime,
        media_type=media_type,
        caption=caption,
    )
    return MemoryMediaResponse.model_validate(media)


@router.delete(
    "/patients/{patient_id}/memories/{memory_id}/media/{media_id}",
    status_code=204,
    summary="Delete a media attachment",
)
async def delete_media(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    memory_id: uuid.UUID,
    media_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _caregiver: Annotated[User, Depends(get_current_caregiver)],
) -> None:
    service = MemoryService(db)
    await service.delete_media(patient_id, memory_id, media_id)
