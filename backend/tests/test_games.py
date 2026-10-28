"""
CogniCompanion — Cognitive Games & Personalization Tests (Phase 6)
==================================================================
Validates:
  - Game catalog retrieval
  - Game activity payload generation for all 4 activities:
      1. Memory Match (paired cards)
      2. Picture Recall (patient-grounded visual memory questions)
      3. Sequence Recall (color / pattern sequences)
      4. Object Recall (everyday items recall)
  - Game session recording and metrics persistence
  - Rolling multi-session Adaptive Difficulty Engine:
      - Consistent high score (>=85%) -> Upgrades difficulty
      - Consistent low score (<60%)   -> Downgrades difficulty
      - Mid-range score (60-84%)       -> Maintains difficulty
  - Strict Patient Memory Isolation & Zero Data Leakage
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.games.models import DifficultyLevel, GameType
from app.domains.memories.models import Memory, MemoryType, Person
from app.domains.patients.models import Patient, User, UserRole


class TestCognitiveGames:

    @pytest.mark.asyncio
    async def test_game_catalog(self, client: AsyncClient, auth_headers: dict):
        """Fetches the available cognitive games catalog."""
        resp = await client.get("/api/v1/games", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_memory_match_generation(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """Generates a Memory Match card pairing deck."""
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/games/MEMORY_MATCH/generate?difficulty=EASY",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_type"] == "MEMORY_MATCH"
        assert data["difficulty_level"] == "EASY"
        assert "cards" in data and len(data["cards"]) == 4  # 2 pairs

        # Verify cards have matching pair_ids
        pair_ids = [c["pair_id"] for c in data["cards"]]
        assert len(set(pair_ids)) == 2

    @pytest.mark.asyncio
    async def test_picture_recall_generation(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, db: AsyncSession
    ):
        """Generates multiple choice questions grounded in patient's memories."""
        p = Person(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Rahul",
            relationship="Grandson",
        )
        db.add(p)
        await db.flush()

        mem = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.VISIT,
            title="Rahul visit and tea",
            description="Rahul brought tea and sweets.",
            event_date=date.today(),
            people=[p],
        )
        db.add(mem)
        await db.flush()

        resp = await client.post(
            f"/api/v1/patients/{patient.id}/games/PICTURE_RECALL/generate",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_type"] == "PICTURE_RECALL"
        assert data["is_personalized"] is True
        assert len(data["questions"]) >= 1
        q = data["questions"][0]
        assert "Rahul" in q["correct_option"]
        assert len(q["options"]) == 4

    @pytest.mark.asyncio
    async def test_sequence_recall_generation(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """Generates color sequences tailored to difficulty."""
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/games/SEQUENCE_RECALL/generate?difficulty=MEDIUM",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_type"] == "SEQUENCE_RECALL"
        assert len(data["sequence"]) == 4

    @pytest.mark.asyncio
    async def test_object_recall_generation(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """Generates familiar everyday objects for recall challenge."""
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/games/OBJECT_RECALL/generate?difficulty=EASY",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_type"] == "OBJECT_RECALL"
        assert len(data["target_objects"]) == 3
        assert len(data["candidate_objects"]) >= len(data["target_objects"])

    @pytest.mark.asyncio
    async def test_game_session_recording(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """Records completed session with performance metrics."""
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/games/sessions",
            headers=auth_headers,
            json={
                "game_type": "MEMORY_MATCH",
                "difficulty_level": "EASY",
                "score": 85,
                "accuracy": 0.85,
                "reaction_time_ms": 1200,
                "mistakes": 1,
                "total_items": 4,
                "correct_items": 3,
                "duration_seconds": 45,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["score"] == 85
        assert data["status"] == "COMPLETED"
        assert data["next_difficulty"] in ["EASY", "MEDIUM", "HARD"]

    @pytest.mark.asyncio
    async def test_difficulty_increases_after_consistent_high_score(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """High rolling average (>=85%) upgrades difficulty level from EASY to MEDIUM."""
        # 3 high score sessions
        for _ in range(3):
            resp = await client.post(
                f"/api/v1/patients/{patient.id}/games/sessions",
                headers=auth_headers,
                json={
                    "game_type": "SEQUENCE_RECALL",
                    "difficulty_level": "EASY",
                    "score": 95,
                    "accuracy": 0.95,
                    "reaction_time_ms": 800,
                    "mistakes": 0,
                    "total_items": 3,
                    "correct_items": 3,
                },
            )
            assert resp.status_code == 201

        data = resp.json()
        assert data["next_difficulty"] == "MEDIUM"

    @pytest.mark.asyncio
    async def test_difficulty_decreases_after_consistent_low_score(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """Low rolling average (<60%) downgrades difficulty level from HARD to MEDIUM."""
        for _ in range(3):
            resp = await client.post(
                f"/api/v1/patients/{patient.id}/games/sessions",
                headers=auth_headers,
                json={
                    "game_type": "OBJECT_RECALL",
                    "difficulty_level": "HARD",
                    "score": 40,
                    "accuracy": 0.40,
                    "reaction_time_ms": 3000,
                    "mistakes": 4,
                    "total_items": 5,
                    "correct_items": 2,
                },
            )
            assert resp.status_code == 201

        data = resp.json()
        assert data["next_difficulty"] == "MEDIUM"

    @pytest.mark.asyncio
    async def test_difficulty_remains_for_mid_range_score(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """Mid-range accuracy (70%) maintains current difficulty level."""
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/games/sessions",
            headers=auth_headers,
            json={
                "game_type": "MEMORY_MATCH",
                "difficulty_level": "MEDIUM",
                "score": 70,
                "accuracy": 0.70,
                "reaction_time_ms": 1500,
                "mistakes": 2,
                "total_items": 6,
                "correct_items": 4,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["next_difficulty"] == "MEDIUM"

    @pytest.mark.asyncio
    async def test_personalized_game_uses_patient_memory(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, db: AsyncSession
    ):
        """Memory Match uses patient's registered family member when available."""
        p = Person(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Ananya",
            relationship="Daughter",
        )
        db.add(p)
        await db.flush()

        resp = await client.post(
            f"/api/v1/patients/{patient.id}/games/MEMORY_MATCH/generate?difficulty=EASY",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_personalized"] is True
        card_labels = [c["label"] for c in data["cards"]]
        assert "Ananya" in card_labels

    @pytest.mark.asyncio
    async def test_personalized_game_does_not_leak_other_patient_data(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, db: AsyncSession
    ):
        """Patient A's game never contains names/photos from Patient B."""
        # Create Patient B
        other_user = User(
            id=uuid.uuid4(),
            email="patient_secret@test.com",
            full_name="Secret User",
            hashed_password="hash",
            role=UserRole.PATIENT,
        )
        db.add(other_user)
        await db.flush()

        patient_b = Patient(id=uuid.uuid4(), user_id=other_user.id)
        db.add(patient_b)
        await db.flush()

        # Add private person belonging exclusively to Patient B
        p_b = Person(
            id=uuid.uuid4(),
            patient_id=patient_b.id,
            name="SecretRelativeX",
            relationship="Confidential Cousin",
        )
        db.add(p_b)
        await db.flush()

        # Generate game for Patient A (must NOT contain SecretRelativeX)
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/games/MEMORY_MATCH/generate",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        card_labels = [c["label"] for c in data["cards"]]
        assert "SecretRelativeX" not in card_labels
