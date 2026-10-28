"""
CogniCompanion — Timeline Router
=====================================
Medications, Routines, Events, and unified Timeline view.
"""

import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import (
    get_current_caregiver,
    get_current_user,
    verify_caregiver_patient_access,
    verify_patient_self_or_caregiver_access,
)
from app.domains.patients.models import User
from app.domains.timeline.schemas import (
    AdherenceLogResponse,
    CreateEventRequest,
    CreateMedicationRequest,
    CreateRoutineRequest,
    EventResponse,
    LogMedicationRequest,
    MedicationResponse,
    RoutineResponse,
    TimelineEntryResponse,
    UpdateEventRequest,
    UpdateMedicationRequest,
    UpdateRoutineRequest,
)
from app.domains.timeline.service import (
    EventService,
    MedicationService,
    RoutineService,
    TimelineService,
)

router = APIRouter(tags=["Timeline"])


# ─────────────────────────────────────────────────────────────────────────────
# MEDICATIONS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/patients/{patient_id}/medications",
    response_model=MedicationResponse,
    status_code=201,
    summary="Add a medication",
)
async def create_medication(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    body: CreateMedicationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_caregiver)],
) -> MedicationResponse:
    service = MedicationService(db)
    med = await service.create(patient_id, body)
    return MedicationResponse.model_validate(med)


@router.get(
    "/patients/{patient_id}/medications",
    response_model=list[MedicationResponse],
    summary="List active medications",
)
async def list_medications(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MedicationResponse]:
    service = MedicationService(db)
    meds = await service.list_active(patient_id)
    return [MedicationResponse.model_validate(m) for m in meds]


@router.patch(
    "/patients/{patient_id}/medications/{medication_id}",
    response_model=MedicationResponse,
    summary="Update a medication",
)
async def update_medication(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    medication_id: uuid.UUID,
    body: UpdateMedicationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_caregiver)],
) -> MedicationResponse:
    service = MedicationService(db)
    med = await service.update(patient_id, medication_id, body)
    return MedicationResponse.model_validate(med)


@router.post(
    "/patients/{patient_id}/medications/{medication_id}/log",
    response_model=AdherenceLogResponse,
    status_code=201,
    summary="Log medication adherence",
)
async def log_medication(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    medication_id: uuid.UUID,
    body: LogMedicationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AdherenceLogResponse:
    """
    Record whether a medication was taken. One entry per medication per day.
    Publishes MedicationTakenEvent when taken=True.
    """
    service = MedicationService(db)
    log = await service.log_adherence(patient_id, medication_id, body, current_user)
    return AdherenceLogResponse.model_validate(log)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTINES
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/patients/{patient_id}/routines",
    response_model=RoutineResponse,
    status_code=201,
    summary="Create a daily routine",
)
async def create_routine(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    body: CreateRoutineRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_caregiver)],
) -> RoutineResponse:
    service = RoutineService(db)
    routine = await service.create(patient_id, body)
    return RoutineResponse.model_validate(routine)


@router.get(
    "/patients/{patient_id}/routines",
    response_model=list[RoutineResponse],
    summary="List active daily routines",
)
async def list_routines(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[RoutineResponse]:
    service = RoutineService(db)
    routines = await service.list_active(patient_id)
    return [RoutineResponse.model_validate(r) for r in routines]


@router.patch(
    "/patients/{patient_id}/routines/{routine_id}",
    response_model=RoutineResponse,
    summary="Update a routine",
)
async def update_routine(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    routine_id: uuid.UUID,
    body: UpdateRoutineRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_caregiver)],
) -> RoutineResponse:
    service = RoutineService(db)
    routine = await service.update(patient_id, routine_id, body)
    return RoutineResponse.model_validate(routine)


# ─────────────────────────────────────────────────────────────────────────────
# EVENTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/patients/{patient_id}/events",
    response_model=EventResponse,
    status_code=201,
    summary="Create a timeline event",
)
async def create_event(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    body: CreateEventRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventResponse:
    service = EventService(db)
    event = await service.create(patient_id, body, current_user)
    return EventResponse.model_validate(event)


@router.get(
    "/patients/{patient_id}/events",
    response_model=list[EventResponse],
    summary="List events",
)
async def list_events(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    limit: int = Query(default=50, le=200),
) -> list[EventResponse]:
    service = EventService(db)
    events = await service.list_events(
        patient_id,
        start_date=date.fromisoformat(start_date) if start_date else None,
        end_date=date.fromisoformat(end_date) if end_date else None,
        limit=limit,
    )
    return [EventResponse.model_validate(e) for e in events]


@router.patch(
    "/patients/{patient_id}/events/{event_id}",
    response_model=EventResponse,
    summary="Update an event",
)
async def update_event(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    event_id: uuid.UUID,
    body: UpdateEventRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_caregiver)],
) -> EventResponse:
    service = EventService(db)
    event = await service.update(patient_id, event_id, body)
    return EventResponse.model_validate(event)


@router.delete(
    "/patients/{patient_id}/events/{event_id}",
    status_code=204,
    summary="Delete an event",
)
async def delete_event(
    patient_id: Annotated[uuid.UUID, Depends(verify_caregiver_patient_access)],
    event_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_caregiver)],
) -> None:
    service = EventService(db)
    await service.delete(patient_id, event_id)


# ─────────────────────────────────────────────────────────────────────────────
# UNIFIED TIMELINE VIEW
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/patients/{patient_id}/timeline",
    response_model=list[TimelineEntryResponse],
    summary="Get unified day timeline (routines + meds + events)",
)
async def get_timeline(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    day: str = Query(
        default=None,
        description="Date to view (YYYY-MM-DD). Defaults to today.",
    ),
) -> list[TimelineEntryResponse]:
    """
    Returns a chronological, unified view of everything scheduled for the day:
    - Routines active on this day of the week
    - Medications (with today's adherence status)
    - Timeline events

    This is the primary endpoint for the **patient's home screen day-view**.
    """
    target_day = date.fromisoformat(day) if day else date.today()
    service = TimelineService(db)
    return await service.get_day_timeline(patient_id, target_day)


# ─────────────────────────────────────────────────────────────────────────────
# OFFLINE SYNCHRONIZATION
# ─────────────────────────────────────────────────────────────────────────────

from app.domains.timeline.offline_sync import (
    BatchSyncRequest,
    BatchSyncResponse,
    OfflineSyncService,
)


@router.post(
    "/patients/{patient_id}/sync",
    response_model=BatchSyncResponse,
    summary="Synchronize offline events in batch with client idempotency",
)
async def sync_offline_events(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    body: BatchSyncRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BatchSyncResponse:
    """
    Synchronizes structured offline actions (game sessions, medication logs, routine check-ins)
    recorded while the device was disconnected.

    Guarantees idempotency via `client_event_id` so retried requests never cause duplicates.
    Automatically refreshes daily performance statistics and CPI metrics for affected dates.
    """
    service = OfflineSyncService(db)
    return await service.sync_batch(patient_id, body.events)
