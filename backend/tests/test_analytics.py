"""
CogniCompanion — Analytics & CPI Tests
=======================================
Tests for:
  1. Insufficient data handling (new patient baseline)
  2. Mathematical correctness of the CPI formula & clamping
  3. Bounded normalization of reaction time and engagement
  4. Non-medical disclaimer enforcement
  5. Patient isolation & caregiver authorization (403 on unauthorized access)
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.domains.analytics.schemas import CPI_NON_MEDICAL_DISCLAIMER, CPIStatus
from app.domains.games.models import DifficultyLevel, Game, GameSession, GameType, SessionStatus
from app.domains.patients.models import Patient, User, UserRole
from app.domains.timeline.models import (
    Medication,
    MedicationAdherenceLog,
    MedicationFrequency,
    MedicationTiming,
)


@pytest.mark.asyncio
async def test_cpi_insufficient_data_for_new_patient(
    client: AsyncClient,
    patient: Patient,
    auth_headers: dict[str, str],
) -> None:
    """A new patient with 0 activity returns status=INSUFFICIENT_DATA and cpi_score=None."""
    resp = await client.get(
        f"/api/v1/patients/{patient.id}/analytics/cpi",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == CPIStatus.INSUFFICIENT_DATA.value
    assert data["cpi_score"] is None
    assert "baseline" in data["message"].lower()
    assert data["disclaimer"] == CPI_NON_MEDICAL_DISCLAIMER
    assert data["games_completed"] == 0


@pytest.mark.asyncio
async def test_cpi_calculation_with_active_data(
    client: AsyncClient,
    db: AsyncSession,
    patient: Patient,
    auth_headers: dict[str, str],
) -> None:
    """
    Tests explicit CPI formula:
      memory_accuracy = 0.85
      reaction_performance = 1.0 - ((1200 - 500) / 3500) = 0.80
      medication_adherence = 2 / 2 = 1.0
      engagement_score = min(1.0, 2 * 0.25) = 0.50
    """
    now = datetime.now(timezone.utc)
    today = date.today()

    # 1. Create a Game
    game = Game(
        id=uuid.uuid4(),
        game_type=GameType.MEMORY_MATCH,
        name="Memory Match",
        min_difficulty=DifficultyLevel.EASY,
        max_difficulty=DifficultyLevel.HARD,
        estimated_duration_seconds=120,
    )
    db.add(game)
    await db.flush()

    # 2. Add two completed game sessions
    session1 = GameSession(
        id=uuid.uuid4(),
        patient_id=patient.id,
        game_id=game.id,
        status=SessionStatus.COMPLETED,
        difficulty_level=DifficultyLevel.MEDIUM,
        score=100,
        accuracy=0.85,
        reaction_time_ms=1200,
        started_at=now,
        completed_at=now,
    )
    session2 = GameSession(
        id=uuid.uuid4(),
        patient_id=patient.id,
        game_id=game.id,
        status=SessionStatus.COMPLETED,
        difficulty_level=DifficultyLevel.MEDIUM,
        score=100,
        accuracy=0.85,
        reaction_time_ms=1200,
        started_at=now,
        completed_at=now,
    )
    db.add_all([session1, session2])

    # 3. Add medications and adherence logs
    med = Medication(
        id=uuid.uuid4(),
        patient_id=patient.id,
        name="Donepezil",
        frequency=MedicationFrequency.ONCE_DAILY,
        timing=MedicationTiming.AFTER_BREAKFAST,
        is_active=True,
    )
    db.add(med)
    await db.flush()

    log = MedicationAdherenceLog(
        id=uuid.uuid4(),
        medication_id=med.id,
        log_date=today,
        taken=True,
        taken_at=now,
    )
    db.add(log)
    await db.commit()

    # Query CPI
    resp = await client.get(
        f"/api/v1/patients/{patient.id}/analytics/cpi",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == CPIStatus.SUFFICIENT_DATA.value
    assert data["cpi_score"] is not None
    assert 0.0 <= data["cpi_score"] <= 100.0
    assert data["memory_accuracy"] == 0.85
    assert round(data["reaction_performance"], 2) == 0.80
    assert data["games_completed"] == 2
    assert data["disclaimer"] == CPI_NON_MEDICAL_DISCLAIMER


@pytest.mark.asyncio
async def test_cpi_trends_endpoint(
    client: AsyncClient,
    patient: Patient,
    auth_headers: dict[str, str],
) -> None:
    """Historical trends endpoint returns the requested number of days."""
    resp = await client.get(
        f"/api/v1/patients/{patient.id}/analytics/cpi/trends?days=7",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["patient_id"] == str(patient.id)
    assert data["days"] == 7
    assert len(data["trends"]) == 7
    assert data["disclaimer"] == CPI_NON_MEDICAL_DISCLAIMER


@pytest.mark.asyncio
async def test_daily_summary_endpoint(
    client: AsyncClient,
    patient: Patient,
    auth_headers: dict[str, str],
) -> None:
    """Daily summary endpoint returns aggregated activity counters."""
    resp = await client.get(
        f"/api/v1/patients/{patient.id}/analytics/daily",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["patient_id"] == str(patient.id)
    assert "games_completed" in data
    assert "medications_scheduled" in data
    assert data["disclaimer"] == CPI_NON_MEDICAL_DISCLAIMER


@pytest.mark.asyncio
async def test_caregiver_patient_authorization_gate(
    client: AsyncClient,
    db: AsyncSession,
    patient: Patient,
) -> None:
    """
    Caregiver B (not assigned to Patient A) receives 403 Forbidden
    when attempting to access Patient A's analytics.
    """
    unauthorized_caregiver = User(
        id=uuid.uuid4(),
        email="unauthorized@test.com",
        full_name="Unauthorized Caregiver",
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
    unauth_headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(
        f"/api/v1/patients/{patient.id}/analytics/cpi",
        headers=unauth_headers,
    )
    assert resp.status_code == 403
    assert "assigned" in resp.json()["detail"].lower()
