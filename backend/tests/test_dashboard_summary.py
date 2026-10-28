"""
CogniCompanion — Caregiver Dashboard Summary Tests (Phase 9)
=============================================================
Tests for:
  1. Aggregated dashboard summary endpoint for assigned caregivers
  2. Patient-isolation authorization gate (403 for unassigned caregivers)
  3. Unauthenticated access prevention (401)
  4. Response accuracy across today's adherence, memory count, and cognitive status
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.domains.memories.models import Memory, MemoryType, Person
from app.domains.patients.models import Patient, User, UserRole
from app.domains.timeline.models import (
    Medication,
    MedicationAdherenceLog,
    MedicationFrequency,
    MedicationTiming,
    Routine,
    RoutineCategory,
)


@pytest.mark.asyncio
async def test_dashboard_summary_authorized_caregiver(
    client: AsyncClient,
    db: AsyncSession,
    patient: Patient,
    auth_headers: dict[str, str],
) -> None:
    """Authorized caregiver receives full aggregated dashboard metrics."""
    now = datetime.now(timezone.utc)
    today = date.today()

    # 1. Add known person & memory
    person = Person(
        id=uuid.uuid4(),
        patient_id=patient.id,
        name="Sunita",
        relationship="sister",
        is_active=True,
    )
    memory = Memory(
        id=uuid.uuid4(),
        patient_id=patient.id,
        memory_type=MemoryType.VISIT,
        title="Sunita brought sweets",
        event_date=today,
        is_significant=True,
    )
    db.add_all([person, memory])

    # 2. Add medication and adherence log
    med1 = Medication(
        id=uuid.uuid4(),
        patient_id=patient.id,
        name="Donepezil 5mg",
        frequency=MedicationFrequency.ONCE_DAILY,
        timing=MedicationTiming.AFTER_BREAKFAST,
        is_active=True,
    )
    med2 = Medication(
        id=uuid.uuid4(),
        patient_id=patient.id,
        name="Multivitamin",
        frequency=MedicationFrequency.ONCE_DAILY,
        timing=MedicationTiming.AFTER_LUNCH,
        is_active=True,
    )
    db.add_all([med1, med2])
    await db.flush()

    log = MedicationAdherenceLog(
        id=uuid.uuid4(),
        medication_id=med1.id,
        log_date=today,
        taken=True,
        taken_at=now,
    )
    db.add(log)

    # 3. Add routine
    routine = Routine(
        id=uuid.uuid4(),
        patient_id=patient.id,
        title="Garden Stroll",
        category=RoutineCategory.MORNING,
        scheduled_time=now.time(),
        days_of_week=127,
        is_active=True,
    )
    db.add(routine)
    await db.commit()

    resp = await client.get(
        f"/api/v1/patients/{patient.id}/dashboard-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Verify structure
    assert "patient" in data
    assert "today" in data
    assert "cognitive" in data
    assert "memory" in data
    assert "attention" in data

    # Verify data content
    assert data["patient"]["id"] == str(patient.id)
    assert data["today"]["total_medications"] == 2
    assert data["today"]["taken_medications"] == 1
    assert data["today"]["pending_medications"] == 1
    assert "Multivitamin" in data["attention"]["pending_medication_names"]
    assert data["memory"]["total_memories"] >= 1
    assert data["memory"]["total_people"] >= 1
    assert data["cognitive"]["disclaimer"] is not None


@pytest.mark.asyncio
async def test_dashboard_summary_unauthorized_caregiver_forbidden(
    client: AsyncClient,
    db: AsyncSession,
    patient: Patient,
) -> None:
    """An unauthorized caregiver gets 403 Forbidden."""
    unauthorized_caregiver = User(
        id=uuid.uuid4(),
        email="unassigned_caregiver@test.com",
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

    resp = await client.get(
        f"/api/v1/patients/{patient.id}/dashboard-summary",
        headers=headers,
    )
    assert resp.status_code == 403
    assert "assigned" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_dashboard_summary_unauthenticated_rejected(
    client: AsyncClient,
    patient: Patient,
) -> None:
    """Unauthenticated requests are rejected with 401."""
    resp = await client.get(f"/api/v1/patients/{patient.id}/dashboard-summary")
    assert resp.status_code == 401
