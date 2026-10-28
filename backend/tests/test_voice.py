"""
CogniCompanion — Voice / Assistant Domain Tests (Phase 3 Vertical Slice)
========================================================================
Validates:
  - 4 Core PME Grounding questions:
      1. "Who is Rahul?" → Person + relationship
      2. "Who visited me yesterday?" → Visit memory + timeline
      3. "What should I do this morning?" → Routine + events
      4. "Did I take my morning medicine?" → Medication + today's adherence log
  - Safety & Architecture:
      - Medication missing adherence record returns deterministic caution
      - Low-confidence queries return safe dementia-companion fallback
      - Gemini failure / offline gracefully falls back to deterministic synthesis
      - Conversation persistence & turn scoping to patient
      - Access control: Unauthorized caregiver cannot query patient
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.domains.memories.models import Memory, MemoryType, Person
from app.domains.patients.models import CaregiverPatient, Patient, User, UserRole
from app.domains.timeline.models import (
    Event,
    EventType,
    Medication,
    MedicationAdherenceLog,
    MedicationFrequency,
    MedicationTiming,
    Routine,
    RoutineCategory,
)


# ── Helper Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
async def seeded_patient_context(db: AsyncSession, patient: Patient) -> dict:
    """Seeds rich context for patient: Rahul (person), Visit yesterday, morning routine, morning medicine."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    # 1. Person: Rahul (Son)
    rahul = Person(
        id=uuid.uuid4(),
        patient_id=patient.id,
        name="Rahul Sharma",
        relationship="son",
        description="Your eldest son who lives nearby and visits on weekends.",
        is_active=True,
    )
    db.add(rahul)
    await db.flush()

    # 2. Memory: Yesterday Visit with Rahul
    visit_memory = Memory(
        id=uuid.uuid4(),
        patient_id=patient.id,
        memory_type=MemoryType.VISIT,
        title="Rahul visited with sweet mangoes",
        description="Rahul came over yesterday afternoon. You both had tea and looked through old family photos.",
        event_date=yesterday,
        is_significant=True,
    )
    visit_memory.people.append(rahul)
    db.add(visit_memory)

    # 3. Routine: Morning Chai & Walk
    morning_routine = Routine(
        id=uuid.uuid4(),
        patient_id=patient.id,
        title="Morning Garden Walk & Tea",
        category=RoutineCategory.MORNING,
        scheduled_time=time(8, 0),
        days_of_week=127,  # All days
        is_active=True,
    )
    db.add(morning_routine)

    # 4. Medication: Donepezil (Morning)
    donepezil = Medication(
        id=uuid.uuid4(),
        patient_id=patient.id,
        name="Donepezil",
        dosage="5 mg",
        frequency=MedicationFrequency.ONCE_DAILY,
        timing=MedicationTiming.AFTER_BREAKFAST,
        is_active=True,
    )
    db.add(donepezil)
    await db.flush()

    return {
        "patient": patient,
        "rahul": rahul,
        "visit_memory": visit_memory,
        "morning_routine": morning_routine,
        "donepezil": donepezil,
    }


# ── Core Demo Question Tests ──────────────────────────────────────────────────

class TestPMEVerticalSlice:
    @pytest.mark.asyncio
    async def test_ask_assistant_person_query(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, seeded_patient_context: dict
    ):
        """Query: 'Who is Rahul?' → Retrieves Person + relationship."""
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/conversations/message",
            headers=auth_headers,
            json={"query": "Who is Rahul?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "person_lookup"
        assert data["confidence"] >= 0.90
        assert "Rahul" in data["reply"]
        assert "son" in data["reply"].lower()
        assert len(data["sources"]) > 0
        assert data["sources"][0]["source_type"] == "person"
        assert data["sources"][0]["title"] == "Rahul Sharma"

    @pytest.mark.asyncio
    async def test_ask_assistant_visit_query(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, seeded_patient_context: dict
    ):
        """Query: 'Who visited me yesterday?' → Retrieves Visit memory + timeline."""
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/conversations/message",
            headers=auth_headers,
            json={"query": "Who visited me yesterday?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "visit_recall"
        assert data["confidence"] >= 0.90
        assert "Rahul" in data["reply"]
        assert "yesterday" in data["reply"].lower()
        assert any(s["source_type"] == "memory" for s in data["sources"])

    @pytest.mark.asyncio
    async def test_ask_assistant_routine_query(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, seeded_patient_context: dict
    ):
        """Query: 'What should I do this morning?' → Retrieves Routine + events."""
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/conversations/message",
            headers=auth_headers,
            json={"query": "What should I do this morning?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "daily_routine"
        assert data["confidence"] >= 0.85
        assert "Morning Garden Walk" in data["reply"]
        assert any(s["source_type"] == "routine" for s in data["sources"])

    @pytest.mark.asyncio
    async def test_ask_assistant_medication_query_taken(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, seeded_patient_context: dict, db: AsyncSession
    ):
        """Query: 'Did I take my morning medicine?' when adherence log is recorded as taken."""
        donepezil = seeded_patient_context["donepezil"]
        log = MedicationAdherenceLog(
            id=uuid.uuid4(),
            medication_id=donepezil.id,
            log_date=date.today(),
            taken=True,
            taken_at=datetime.now(timezone.utc),
        )
        db.add(log)
        await db.flush()

        resp = await client.post(
            f"/api/v1/patients/{patient.id}/conversations/message",
            headers=auth_headers,
            json={"query": "Did I take my morning medicine?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "medication_adherence"
        assert data["confidence"] >= 0.95
        # Must deterministically report as taken
        assert "Yes" in data["reply"]
        assert "recorded as taken" in data["reply"].lower()
        assert "Donepezil" in data["reply"]

    @pytest.mark.asyncio
    async def test_medication_missing_adherence_record(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, seeded_patient_context: dict
    ):
        """Query: 'Did I take my morning medicine?' when NO adherence log exists → safe caution."""
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/conversations/message",
            headers=auth_headers,
            json={"query": "Did I take my morning medicine?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "medication_adherence"
        # Must NEVER claim it was taken; must include caregiver safety advisory
        assert "don't have a record" in data["reply"].lower() or "not recorded" in data["reply"].lower()
        assert "caregiver" in data["reply"].lower()

    @pytest.mark.asyncio
    async def test_unknown_question_returns_safe_response(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """Query: Unrelated question → Safe, comforting dementia-friendly response without crash."""
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/conversations/message",
            headers=auth_headers,
            json={"query": "What is the airspeed velocity of an unladen swallow?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] in ["unknown", "general_conversation"]
        assert "here with you" in data["reply"].lower() or "help you" in data["reply"].lower()

    @pytest.mark.asyncio
    async def test_low_confidence_does_not_hallucinate(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, seeded_patient_context: dict
    ):
        """Query for a person NOT in the database ('Who is Vikram?') → Does not hallucinate personal facts."""
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/conversations/message",
            headers=auth_headers,
            json={"query": "Who is Vikram?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should gracefully indicate missing record or suggest known family (Rahul)
        assert "couldn't find" in data["reply"].lower() or "looking through" in data["reply"].lower() or "Rahul" in data["reply"]

    @pytest.mark.asyncio
    async def test_gemini_failure_uses_fallback(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, seeded_patient_context: dict
    ):
        """Simulate LLM error → Backend gracefully returns deterministic grounded synthesis."""
        with patch("app.ai.providers.llm.GeminiLLMProvider.generate", side_effect=Exception("API connection timeout")):
            resp = await client.post(
                f"/api/v1/patients/{patient.id}/conversations/message",
                headers=auth_headers,
                json={"query": "Who is Rahul?"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "Rahul" in data["reply"]
            assert "son" in data["reply"].lower()

    @pytest.mark.asyncio
    async def test_conversation_scoped_to_patient(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """Checks multi-turn conversation and persistence."""
        # Turn 1
        r1 = await client.post(
            f"/api/v1/patients/{patient.id}/conversations/message",
            headers=auth_headers,
            json={"query": "Namaste"},
        )
        assert r1.status_code == 200
        conv_id = r1.json()["conversation_id"]

        # Turn 2 with existing conversation_id
        r2 = await client.post(
            f"/api/v1/patients/{patient.id}/conversations/message",
            headers=auth_headers,
            json={"query": "What is on my schedule today?", "conversation_id": conv_id},
        )
        assert r2.status_code == 200
        assert r2.json()["conversation_id"] == conv_id

        # List conversations
        list_resp = await client.get(
            f"/api/v1/patients/{patient.id}/conversations",
            headers=auth_headers,
        )
        assert list_resp.status_code == 200
        convs = list_resp.json()
        assert len(convs) >= 1
        assert convs[0]["id"] == conv_id
        assert convs[0]["message_count"] >= 4

    @pytest.mark.asyncio
    async def test_unauthorized_caregiver_cannot_access_patient(
        self, client: AsyncClient, db: AsyncSession, patient: Patient
    ):
        """Caregiver B without patient assignment cannot query or access patient conversation (403 Forbidden)."""
        unauthorized_caregiver = User(
            id=uuid.uuid4(),
            email="intruder@test.com",
            full_name="Other Caregiver",
            hashed_password=hash_password("Pass123!"),
            role=UserRole.CAREGIVER,
        )
        db.add(unauthorized_caregiver)
        await db.flush()

        other_token = create_access_token(
            user_id=str(unauthorized_caregiver.id),
            role=unauthorized_caregiver.role.value,
            token_version=unauthorized_caregiver.token_version,
        )
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = await client.post(
            f"/api/v1/patients/{patient.id}/conversations/message",
            headers=other_headers,
            json={"query": "Who visited me yesterday?"},
        )
        assert resp.status_code == 403
