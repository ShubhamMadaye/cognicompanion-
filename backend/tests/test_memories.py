"""
CogniCompanion - Memories Domain Tests
Tests for People CRUD and Memory CRUD.
SQLite in-memory DB - no PostgreSQL needed.
"""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.memories.models import Memory, MemoryType, Person
from app.domains.patients.models import Patient, User

pytestmark = pytest.mark.asyncio


class TestPeopleCRUD:
    async def test_create_person(self, client, patient, auth_headers):
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/people",
            json={"name": "Rahul", "relationship": "son", "description": "Visits every Sunday"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Rahul"
        assert data["patient_id"] == str(patient.id)

    async def test_list_people(self, client, patient, db, auth_headers):
        db.add(Person(patient_id=patient.id, name="Rahul"))
        db.add(Person(patient_id=patient.id, name="Priya"))
        await db.flush()
        resp = await client.get(f"/api/v1/patients/{patient.id}/people", headers=auth_headers)
        assert resp.status_code == 200
        names = [p["name"] for p in resp.json()]
        assert "Rahul" in names and "Priya" in names

    async def test_get_person(self, client, patient, db, auth_headers):
        person = Person(patient_id=patient.id, name="Meena", relationship="daughter")
        db.add(person)
        await db.flush()
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/people/{person.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Meena"

    async def test_update_person(self, client, patient, db, auth_headers):
        person = Person(patient_id=patient.id, name="Suresh")
        db.add(person)
        await db.flush()
        resp = await client.patch(
            f"/api/v1/patients/{patient.id}/people/{person.id}",
            json={"name": "Suresh Kumar", "relationship": "brother"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Suresh Kumar"
        assert resp.json()["relationship"] == "brother"


class TestMemoryCRUD:
    async def test_create_memory_basic(self, client, patient, auth_headers):
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/memories",
            json={
                "memory_type": "VISIT",
                "title": "Rahul visited today",
                "event_date": str(date.today()),
                "is_significant": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["memory_type"] == "VISIT"
        assert data["is_significant"] is True
        assert data["media"] == []
        assert data["people"] == []

    async def test_create_memory_with_person_link(self, client, patient, db, auth_headers):
        person = Person(patient_id=patient.id, name="Rahul")
        db.add(person)
        await db.flush()
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/memories",
            json={
                "memory_type": "VISIT",
                "title": "Rahul visit",
                "event_date": str(date.today()),
                "person_ids": [str(person.id)],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        assert len(resp.json()["people"]) == 1
        assert resp.json()["people"][0]["name"] == "Rahul"

    async def test_list_memories_newest_first(
        self, client, patient, db, caregiver_user, auth_headers
    ):
        for title, d in [("Old", date(2025, 1, 1)), ("New", date(2026, 6, 15))]:
            db.add(Memory(
                patient_id=patient.id,
                created_by=caregiver_user.id,
                memory_type=MemoryType.GENERAL,
                title=title,
                event_date=d,
            ))
        await db.flush()
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/memories", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()[0]["title"] == "New"

    async def test_list_filter_by_type(self, client, patient, db, caregiver_user, auth_headers):
        db.add(Memory(
            patient_id=patient.id, created_by=caregiver_user.id,
            memory_type=MemoryType.VISIT, title="V", event_date=date.today(),
        ))
        db.add(Memory(
            patient_id=patient.id, created_by=caregiver_user.id,
            memory_type=MemoryType.MEAL, title="M", event_date=date.today(),
        ))
        await db.flush()
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/memories?memory_type=VISIT", headers=auth_headers
        )
        assert resp.status_code == 200
        assert all(m["memory_type"] == "VISIT" for m in resp.json())

    async def test_get_memory_full_detail(
        self, client, patient, db, caregiver_user, auth_headers
    ):
        mem = Memory(
            patient_id=patient.id,
            created_by=caregiver_user.id,
            memory_type=MemoryType.APPOINTMENT,
            title="Doctor visit",
            location="City Hospital",
            event_date=date.today(),
        )
        db.add(mem)
        await db.flush()
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/memories/{mem.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["location"] == "City Hospital"
        assert "media" in resp.json()
        assert "people" in resp.json()

    async def test_update_memory(self, client, patient, db, caregiver_user, auth_headers):
        mem = Memory(
            patient_id=patient.id, created_by=caregiver_user.id,
            memory_type=MemoryType.GENERAL, title="Old title", event_date=date.today(),
        )
        db.add(mem)
        await db.flush()
        resp = await client.patch(
            f"/api/v1/patients/{patient.id}/memories/{mem.id}",
            json={"title": "New title", "is_significant": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New title"
        assert resp.json()["is_significant"] is True

    async def test_delete_memory(self, client, patient, db, caregiver_user, auth_headers):
        mem = Memory(
            patient_id=patient.id, created_by=caregiver_user.id,
            memory_type=MemoryType.GENERAL, title="Delete me", event_date=date.today(),
        )
        db.add(mem)
        await db.flush()
        memory_id = mem.id
        resp = await client.delete(
            f"/api/v1/patients/{patient.id}/memories/{memory_id}", headers=auth_headers
        )
        assert resp.status_code == 204
        resp2 = await client.get(
            f"/api/v1/patients/{patient.id}/memories/{memory_id}", headers=auth_headers
        )
        assert resp2.status_code == 404

    async def test_significant_only_filter(
        self, client, patient, db, caregiver_user, auth_headers
    ):
        db.add(Memory(
            patient_id=patient.id, created_by=caregiver_user.id,
            memory_type=MemoryType.GENERAL, title="Sig",
            event_date=date.today(), is_significant=True,
        ))
        db.add(Memory(
            patient_id=patient.id, created_by=caregiver_user.id,
            memory_type=MemoryType.GENERAL, title="Not sig",
            event_date=date.today(), is_significant=False,
        ))
        await db.flush()
        resp = await client.get(
            f"/api/v1/patients/{patient.id}/memories?significant_only=true",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert all(m["is_significant"] for m in resp.json())
