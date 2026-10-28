"""
CogniCompanion — Offline Support & Synchronization
===================================================
Handles batch synchronization of structured events collected while the patient
or caregiver device was offline (e.g. intermittent connectivity in rural areas).

Key Rules:
  1. Idempotency: Uses client_event_id (UUID) to ensure retried requests
     never duplicate game sessions, medication doses, or routine completions.
  2. Structured records only: Game sessions, medication logs, and routine check-ins.
     (Raw voice audio is not queued indefinitely on low-resource devices).
  3. Automatic Analytics Refresh: After syncing, affected daily statistics and
     CPI metrics are recalculated so the Caregiver Dashboard is up to date.
"""

import enum
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.games.models import DifficultyLevel, GameSession, SessionStatus
from app.domains.timeline.models import (
    Event,
    EventType,
    Medication,
    MedicationAdherenceLog,
    Routine,
)

logger = logging.getLogger(__name__)


class SyncEventType(str, enum.Enum):
    MEDICATION_CONFIRMATION = "MEDICATION_CONFIRMATION"
    ROUTINE_CHECK_IN = "ROUTINE_CHECK_IN"
    GAME_SESSION = "GAME_SESSION"


class SyncEventItem(BaseModel):
    client_event_id: uuid.UUID = Field(
        ..., description="Unique client-generated UUID for idempotency"
    )
    event_type: SyncEventType
    client_timestamp: datetime
    payload: dict[str, Any] = Field(
        ..., description="Structured payload matching the event_type"
    )

    model_config = ConfigDict(from_attributes=True)


class SyncStatus(str, enum.Enum):
    PROCESSED = "PROCESSED"
    ALREADY_PROCESSED = "ALREADY_PROCESSED"
    ERROR = "ERROR"


class SyncResultItem(BaseModel):
    client_event_id: uuid.UUID
    event_type: SyncEventType
    status: SyncStatus
    detail: Optional[str] = None


class BatchSyncRequest(BaseModel):
    events: list[SyncEventItem] = Field(
        ..., min_length=1, description="List of offline events to synchronize"
    )


class BatchSyncResponse(BaseModel):
    patient_id: uuid.UUID
    total_events: int
    processed_count: int
    skipped_count: int
    error_count: int
    results: list[SyncResultItem]


class OfflineSyncService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def sync_batch(
        self, patient_id: uuid.UUID, events: list[SyncEventItem]
    ) -> BatchSyncResponse:
        results: list[SyncResultItem] = []
        processed_count = 0
        skipped_count = 0
        error_count = 0
        affected_dates: set[date] = set()

        for item in events:
            try:
                if item.event_type == SyncEventType.MEDICATION_CONFIRMATION:
                    status, detail, log_d = await self._sync_medication(
                        patient_id, item
                    )
                elif item.event_type == SyncEventType.ROUTINE_CHECK_IN:
                    status, detail, log_d = await self._sync_routine(
                        patient_id, item
                    )
                elif item.event_type == SyncEventType.GAME_SESSION:
                    status, detail, log_d = await self._sync_game_session(
                        patient_id, item
                    )
                else:
                    status, detail, log_d = (
                        SyncStatus.ERROR,
                        f"Unsupported event type: {item.event_type}",
                        None,
                    )

                if status == SyncStatus.PROCESSED:
                    processed_count += 1
                    if log_d:
                        affected_dates.add(log_d)
                elif status == SyncStatus.ALREADY_PROCESSED:
                    skipped_count += 1
                elif status == SyncStatus.ERROR:
                    error_count += 1

                results.append(
                    SyncResultItem(
                        client_event_id=item.client_event_id,
                        event_type=item.event_type,
                        status=status,
                        detail=detail,
                    )
                )
            except Exception as exc:
                logger.error(
                    "Error syncing event %s: %s", item.client_event_id, exc
                )
                error_count += 1
                results.append(
                    SyncResultItem(
                        client_event_id=item.client_event_id,
                        event_type=item.event_type,
                        status=SyncStatus.ERROR,
                        detail=str(exc),
                    )
                )

        await self.db.commit()

        # Update Daily Statistics and CPI for affected dates
        if affected_dates:
            try:
                from app.domains.analytics.service import AnalyticsService

                analytics_service = AnalyticsService(self.db)
                for d in affected_dates:
                    await analytics_service.compute_cpi_metric(patient_id, d)
            except Exception as e:
                logger.warning("Could not refresh CPI after sync: %s", e)

        return BatchSyncResponse(
            patient_id=patient_id,
            total_events=len(events),
            processed_count=processed_count,
            skipped_count=skipped_count,
            error_count=error_count,
            results=results,
        )

    async def _sync_medication(
        self, patient_id: uuid.UUID, item: SyncEventItem
    ) -> tuple[SyncStatus, Optional[str], Optional[date]]:
        payload = item.payload
        med_id_str = payload.get("medication_id")
        if not med_id_str:
            return SyncStatus.ERROR, "Missing medication_id", None

        med_id = uuid.UUID(str(med_id_str))
        log_date_val = payload.get("log_date")
        if isinstance(log_date_val, str):
            target_date = date.fromisoformat(log_date_val)
        elif isinstance(log_date_val, date):
            target_date = log_date_val
        else:
            target_date = item.client_timestamp.date()

        taken = bool(payload.get("taken", True))
        notes = payload.get("notes")

        # Idempotency check: Does a log already exist for this (medication, date)?
        stmt = select(MedicationAdherenceLog).where(
            MedicationAdherenceLog.medication_id == med_id,
            MedicationAdherenceLog.log_date == target_date,
        )
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            if existing.taken == taken:
                return SyncStatus.ALREADY_PROCESSED, "Adherence log already recorded", None
            # Update state
            existing.taken = taken
            if notes:
                existing.notes = notes
            return SyncStatus.PROCESSED, "Updated existing adherence log", target_date

        log = MedicationAdherenceLog(
            id=item.client_event_id,
            medication_id=med_id,
            log_date=target_date,
            taken=taken,
            taken_at=item.client_timestamp,
            notes=notes,
        )
        self.db.add(log)
        return SyncStatus.PROCESSED, "Created adherence log", target_date

    async def _sync_routine(
        self, patient_id: uuid.UUID, item: SyncEventItem
    ) -> tuple[SyncStatus, Optional[str], Optional[date]]:
        payload = item.payload
        routine_id_str = payload.get("routine_id")
        if not routine_id_str:
            return SyncStatus.ERROR, "Missing routine_id", None

        routine_id = uuid.UUID(str(routine_id_str))
        target_date = item.client_timestamp.date()
        title = payload.get("title", "Completed Routine")

        # Check if an event already exists with this client_event_id
        event_stmt = select(Event).where(Event.id == item.client_event_id)
        res = await self.db.execute(event_stmt)
        if res.scalar_one_or_none():
            return SyncStatus.ALREADY_PROCESSED, "Routine check-in already recorded", None

        event = Event(
            id=item.client_event_id,
            patient_id=patient_id,
            event_type=EventType.ACTIVITY,
            title=f"Completed: {title}",
            start_time=item.client_timestamp,
            icon_emoji="✓",
        )
        self.db.add(event)
        return SyncStatus.PROCESSED, "Created routine check-in event", target_date

    async def _sync_game_session(
        self, patient_id: uuid.UUID, item: SyncEventItem
    ) -> tuple[SyncStatus, Optional[str], Optional[date]]:
        payload = item.payload
        game_id_str = payload.get("game_id")
        if not game_id_str:
            return SyncStatus.ERROR, "Missing game_id", None

        game_id = uuid.UUID(str(game_id_str))
        target_date = item.client_timestamp.date()

        # Idempotency check: Use client_event_id as GameSession.id
        sess_stmt = select(GameSession).where(
            GameSession.id == item.client_event_id
        )
        res = await self.db.execute(sess_stmt)
        if res.scalar_one_or_none():
            return SyncStatus.ALREADY_PROCESSED, "Game session already recorded", None

        diff_str = payload.get("difficulty_level", "MEDIUM")
        try:
            diff_level = DifficultyLevel(diff_str)
        except ValueError:
            diff_level = DifficultyLevel.MEDIUM

        session = GameSession(
            id=item.client_event_id,
            patient_id=patient_id,
            game_id=game_id,
            status=SessionStatus.COMPLETED,
            difficulty_level=diff_level,
            score=int(payload.get("score", 0)),
            accuracy=float(payload.get("accuracy", 0.0)),
            reaction_time_ms=payload.get("reaction_time_ms"),
            mistakes=int(payload.get("mistakes", 0)),
            started_at=item.client_timestamp,
            completed_at=item.client_timestamp,
        )
        self.db.add(session)
        return SyncStatus.PROCESSED, "Created game session", target_date
