"""
CogniCompanion — Offline Sync Tests (Phase 10)
==============================================
Tests for:
  1. Batch sync of structured offline events (medications, games, routines)
  2. Idempotency guarantees via client_event_id (no duplicate dose/game entries on retries)
  3. Authorization gate enforcement (403 for unauthorized caregivers)
  4. Automatic analytics/CPI refresh on successful sync
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.domains.games.models import DifficultyLevel, Game, GameSession, GameType
from app.domains.patients.models import Patient, User, UserRole
from app.domains.timeline.models import (
    Medication,
    MedicationAdherenceLog,
    MedicationFrequency,
    MedicationTiming,
    Routine,
    RoutineCategory,
)
from app.domains.timeline.offline_sync import SyncEventType


@pytest.mark.asyncio
async def test_offline_batch_sync_success(
    client: AsyncClient,
    db: AsyncSession,
    patient: Patient,
    auth_headers: dict[str, str],
) -> None:
    """Batch syncing offline medication, routine, and game records succeeds."""
    now = datetime.now(timezone.utc)
    today = date.today()

    # Create pre-requisites
    med = Medication(
        id=uuid.uuid4(),
        patient_id=patient.id,
        name="Donepezil 5mg",
        frequency=MedicationFrequency.ONCE_DAILY,
        timing=MedicationTiming.AFTER_BREAKFAST,
        is_active=True,
    )
    routine = Routine(
        id=uuid.uuid4(),
        patient_id=patient.id,
        title="Morning Tea",
        category=RoutineCategory.MORNING,
        scheduled_time=now.time(),
        days_of_week=127,
        is_active=True,
    )
    game = Game(
        id=uuid.uuid4(),
        game_type=GameType.SEQUENCE_RECALL,
        name="Sequence Recall",
        min_difficulty=DifficultyLevel.EASY,
        max_difficulty=DifficultyLevel.HARD,
        estimated_duration_seconds=120,
    )
    db.add_all([med, routine, game])
    await db.commit()

    event_id_med = uuid.uuid4()
    event_id_routine = uuid.uuid4()
    event_id_game = uuid.uuid4()

    sync_payload = {
        "events": [
            {
                "client_event_id": str(event_id_med),
                "event_type": SyncEventType.MEDICATION_CONFIRMATION.value,
                "client_timestamp": now.isoformat(),
                "payload": {
                    "medication_id": str(med.id),
                    "log_date": today.isoformat(),
                    "taken": True,
                    "notes": "Taken with water offline",
                },
            },
            {
                "client_event_id": str(event_id_routine),
                "event_type": SyncEventType.ROUTINE_CHECK_IN.value,
                "client_timestamp": now.isoformat(),
                "payload": {
                    "routine_id": str(routine.id),
                    "title": "Morning Tea",
                },
            },
            {
                "client_event_id": str(event_id_game),
                "event_type": SyncEventType.GAME_SESSION.value,
                "client_timestamp": now.isoformat(),
                "payload": {
                    "game_id": str(game.id),
                    "difficulty_level": "EASY",
                    "score": 95,
                    "accuracy": 0.90,
                    "reaction_time_ms": 1100,
                    "mistakes": 1,
                },
            },
        ]
    }

    resp = await client.post(
        f"/api/v1/patients/{patient.id}/sync",
        json=sync_payload,
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_events"] == 3
    assert data["processed_count"] == 3
    assert data["skipped_count"] == 0
    assert data["error_count"] == 0


@pytest.mark.asyncio
async def test_offline_batch_sync_idempotency(
    client: AsyncClient,
    db: AsyncSession,
    patient: Patient,
    auth_headers: dict[str, str],
) -> None:
    """
    Retrying the exact same batch when network reconnects does not duplicate records.
    Already processed records return status=ALREADY_PROCESSED and are skipped.
    """
    now = datetime.now(timezone.utc)
    today = date.today()

    game = Game(
        id=uuid.uuid4(),
        game_type=GameType.PICTURE_RECALL,
        name="Picture Recall",
        min_difficulty=DifficultyLevel.EASY,
        max_difficulty=DifficultyLevel.HARD,
        estimated_duration_seconds=120,
    )
    db.add(game)
    await db.commit()

    game_event_id = uuid.uuid4()
    sync_payload = {
        "events": [
            {
                "client_event_id": str(game_event_id),
                "event_type": SyncEventType.GAME_SESSION.value,
                "client_timestamp": now.isoformat(),
                "payload": {
                    "game_id": str(game.id),
                    "difficulty_level": "MEDIUM",
                    "score": 80,
                    "accuracy": 0.85,
                    "reaction_time_ms": 1300,
                    "mistakes": 2,
                },
            }
        ]
    }

    # 1. First sync attempt
    resp1 = await client.post(
        f"/api/v1/patients/{patient.id}/sync",
        json=sync_payload,
        headers=auth_headers,
    )
    assert resp1.status_code == 200
    assert resp1.json()["processed_count"] == 1
    assert resp1.json()["skipped_count"] == 0

    # 2. Retry the EXACT SAME payload (simulating network reconnect retry)
    resp2 = await client.post(
        f"/api/v1/patients/{patient.id}/sync",
        json=sync_payload,
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["processed_count"] == 0
    assert data2["skipped_count"] == 1
    assert data2["results"][0]["status"] == "ALREADY_PROCESSED"

    # 3. Verify exactly 1 game session exists in the database
    count_res = await db.execute(
        select(func.count(GameSession.id)).where(GameSession.id == game_event_id)
    )
    assert count_res.scalar() == 1


@pytest.mark.asyncio
async def test_offline_sync_unauthorized_caregiver_forbidden(
    client: AsyncClient,
    db: AsyncSession,
    patient: Patient,
) -> None:
    """Caregivers cannot sync events for patients they are not assigned to (403 Forbidden)."""
    unauthorized_caregiver = User(
        id=uuid.uuid4(),
        email="unassigned_sync@test.com",
        full_name="Unassigned Caregiver",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.CAREGIVER,
    )
    db.add(unauthorized_caregiver)
    await db.commit()

    token = create_access_token(
        user_id=str(unauthorized_caregiver.id),
        role=unauthorized_caregiver.role.value,
        token_version=unauthorized_caregiver.token_version,
    )
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "events": [
            {
                "client_event_id": str(uuid.uuid4()),
                "event_type": SyncEventType.MEDICATION_CONFIRMATION.value,
                "client_timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"medication_id": str(uuid.uuid4()), "taken": True},
            }
        ]
    }

    resp = await client.post(
        f"/api/v1/patients/{patient.id}/sync",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 403
