"""
CogniCompanion - Timeline Domain Tests
Tests for Medications, Routines, Events, and the unified Day View.
Includes the new memory kind in the timeline.
"""

from datetime import date, datetime, time, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.memories.models import Memory, MemoryType
from app.domains.patients.models import Patient, User
from app.domains.timeline.models import (
    Event,
    EventType,
    Medication,
    MedicationFrequency,
    MedicationTiming,
    Routine,
    RoutineCategory,
)

pytestmark = pytest.mark.asyncio

TODAY = date.today().isoformat()


class TestMedications:
    async def test_create_medication(self, client, patient, auth_headers):
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/medications",
            json={
                "name": "Metformin",
                "dosage": "500mg",
                "frequency": "TWICE_DAILY",
                "timing": "AFTER_BREAKFAST",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["name"] == "Metformin"
        assert resp.json()["is_active"] is True

    async def test_list_active_medications(self, client, patient, db, auth_headers):
        db.add(Medication(
            patient_id=patient.id,
            name="Aspirin",
            frequency=MedicationFrequency.ONCE_DAILY,
            timing=MedicationTiming.AFTER_BREAKFAST,
        ))
        await db.flush()
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/medications", headers=auth_headers
        )
        assert resp.status_code == 200
        assert any(m["name"] == "Aspirin" for m in resp.json())

    async def test_update_medication(self, client, patient, db, auth_headers):
        med = Medication(
            patient_id=patient.id,
            name="Metformin",
            frequency=MedicationFrequency.ONCE_DAILY,
            timing=MedicationTiming.AFTER_DINNER,
        )
        db.add(med)
        await db.flush()
        resp = await client.patch(
            f"/api/v1/patients/{patient.id}/medications/{med.id}",
            json={"dosage": "1000mg"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["dosage"] == "1000mg"


class TestRoutines:
    async def test_create_routine(self, client, patient, auth_headers):
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/routines",
            json={
                "title": "Morning Walk",
                "category": "MORNING",
                "scheduled_time": "07:00:00",
                "days_of_week": 127,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["title"] == "Morning Walk"
        assert resp.json()["days_of_week"] == 127

    async def test_list_routines(self, client, patient, db, auth_headers):
        db.add(Routine(
            patient_id=patient.id,
            title="Evening Yoga",
            category=RoutineCategory.EVENING,
            scheduled_time=time(18, 0),
        ))
        await db.flush()
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/routines", headers=auth_headers
        )
        assert resp.status_code == 200
        assert any(r["title"] == "Evening Yoga" for r in resp.json())

    async def test_update_routine(self, client, patient, db, auth_headers):
        routine = Routine(
            patient_id=patient.id,
            title="Old title",
            category=RoutineCategory.MORNING,
            scheduled_time=time(8, 0),
        )
        db.add(routine)
        await db.flush()
        resp = await client.patch(
            f"/api/v1/patients/{patient.id}/routines/{routine.id}",
            json={"title": "New title"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New title"


class TestEvents:
    async def test_create_event(self, client, patient, auth_headers):
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/events",
            json={
                "event_type": "APPOINTMENT",
                "title": "Cardiology Check-up",
                "start_time": f"{TODAY}T10:00:00Z",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["title"] == "Cardiology Check-up"

    async def test_list_events(self, client, patient, db, caregiver_user, auth_headers):
        db.add(Event(
            patient_id=patient.id,
            created_by=caregiver_user.id,
            event_type=EventType.VISIT,
            title="Family visit",
            start_time=datetime.now(timezone.utc),
        ))
        await db.flush()
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/events", headers=auth_headers
        )
        assert resp.status_code == 200
        assert any(e["title"] == "Family visit" for e in resp.json())

    async def test_delete_event(self, client, patient, db, caregiver_user, auth_headers):
        ev = Event(
            patient_id=patient.id,
            created_by=caregiver_user.id,
            event_type=EventType.GENERAL,
            title="Temp",
            start_time=datetime.now(timezone.utc),
        )
        db.add(ev)
        await db.flush()
        resp = await client.delete(
            f"/api/v1/patients/{patient.id}/events/{ev.id}", headers=auth_headers
        )
        assert resp.status_code == 204


class TestUnifiedTimeline:
    async def test_day_view_returns_list(self, client, patient, auth_headers):
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/timeline?day={TODAY}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_day_view_defaults_to_today(self, client, patient, auth_headers):
        """No day param defaults to today without error."""
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/timeline", headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_day_view_includes_visit_memory(
        self, client, patient, db, caregiver_user, auth_headers
    ):
        """VISIT memories on the queried day appear as kind=memory in the timeline."""
        db.add(Memory(
            patient_id=patient.id,
            created_by=caregiver_user.id,
            memory_type=MemoryType.VISIT,
            title="Son visited",
            event_date=date.today(),
        ))
        await db.flush()
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/timeline?day={TODAY}", headers=auth_headers
        )
        assert resp.status_code == 200
        kinds = [e["kind"] for e in resp.json()]
        assert "memory" in kinds
        memory_entries = [e for e in resp.json() if e["kind"] == "memory"]
        assert memory_entries[0]["title"] == "Son visited"
        assert memory_entries[0]["metadata"]["memory_type"] == "VISIT"

    async def test_day_view_appointment_memory_in_timeline(
        self, client, patient, db, caregiver_user, auth_headers
    ):
        """APPOINTMENT memories also appear in the day timeline."""
        db.add(Memory(
            patient_id=patient.id,
            created_by=caregiver_user.id,
            memory_type=MemoryType.APPOINTMENT,
            title="Dr Sharma appointment",
            event_date=date.today(),
        ))
        await db.flush()
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/timeline?day={TODAY}", headers=auth_headers
        )
        assert resp.status_code == 200
        memory_entries = [e for e in resp.json() if e["kind"] == "memory"]
        assert any(e["metadata"]["memory_type"] == "APPOINTMENT" for e in memory_entries)

    async def test_day_view_excludes_general_memories(
        self, client, patient, db, caregiver_user, auth_headers
    ):
        """GENERAL and MEAL memories do NOT surface in the day timeline."""
        db.add(Memory(
            patient_id=patient.id,
            created_by=caregiver_user.id,
            memory_type=MemoryType.GENERAL,
            title="General note",
            event_date=date.today(),
        ))
        db.add(Memory(
            patient_id=patient.id,
            created_by=caregiver_user.id,
            memory_type=MemoryType.MEAL,
            title="Lunch",
            event_date=date.today(),
        ))
        await db.flush()
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/timeline?day={TODAY}", headers=auth_headers
        )
        assert resp.status_code == 200
        memory_entries = [e for e in resp.json() if e["kind"] == "memory"]
        for entry in memory_entries:
            assert entry["metadata"]["memory_type"] in ("VISIT", "OUTING", "APPOINTMENT")

    async def test_day_view_excludes_other_day_memories(
        self, client, patient, db, caregiver_user, auth_headers
    ):
        """Memories from a different day do not appear."""
        db.add(Memory(
            patient_id=patient.id,
            created_by=caregiver_user.id,
            memory_type=MemoryType.VISIT,
            title="Yesterday visit",
            event_date=date(2025, 1, 1),
        ))
        await db.flush()
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/timeline?day={TODAY}", headers=auth_headers
        )
        assert resp.status_code == 200
        titles = [e["title"] for e in resp.json()]
        assert "Yesterday visit" not in titles

    async def test_day_view_includes_routine_and_memory(
        self, client, patient, db, caregiver_user, auth_headers
    ):
        """Routines and memories coexist in the same day view correctly."""
        # Add a Monday-active routine
        db.add(Routine(
            patient_id=patient.id,
            title="Morning Walk",
            category=RoutineCategory.MORNING,
            scheduled_time=time(7, 0),
            days_of_week=127,  # all days
        ))
        db.add(Memory(
            patient_id=patient.id,
            created_by=caregiver_user.id,
            memory_type=MemoryType.OUTING,
            title="Park outing",
            event_date=date.today(),
        ))
        await db.flush()
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/timeline?day={TODAY}", headers=auth_headers
        )
        assert resp.status_code == 200
        result = resp.json()
        assert any(e["kind"] == "routine" for e in result)
        assert any(e["kind"] == "memory" for e in result)
