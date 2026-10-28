"""
CogniCompanion — PME Semantic & Hybrid Retrieval Tests (Phase 4)
================================================================
Validates:
  - Embeddings generation & updates on domain events
  - Semantic vector search with cosine similarity
  - Similarity threshold enforcement
  - Patient isolation (strict scoping)
  - Hybrid retrieval (combining structured + semantic)
  - Significance-aware ranking boost (is_significant)
  - Failure handling (API failure does not break memory creation)
  - Narrative queries & grounded sources attribution
"""

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory_engine.semantic_retriever import SemanticRetriever
from app.events.bus import event_bus, MemoryCreatedEvent
from app.events.handlers import handle_memory_created_generate_embedding
from app.domains.memories.models import Memory, MemoryType, Person
from app.domains.patients.models import CaregiverPatient, Patient, User, UserRole
from app.domains.voice.models import MemoryEmbedding


# ── Helper Vector Generator ───────────────────────────────────────────────────

def create_synthetic_vector(seed_value: float, dim: int = 768) -> list[float]:
    """Generates a synthetic normalized vector with a distinctive directional bias."""
    vec = [0.0] * dim
    vec[0] = seed_value
    vec[1] = 1.0 - abs(seed_value)
    return vec


# ── Test Suite ────────────────────────────────────────────────────────────────

class TestPMESemanticAndHybrid:

    @pytest.mark.asyncio
    async def test_embedding_generation_on_memory_creation(
        self, db: AsyncSession, patient: Patient
    ):
        """Asynchronous event handler generates and stores MemoryEmbedding row."""
        mem = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.VISIT,
            title="Temple trip with daughter",
            description="We visited the Kamakhya temple and offered marigold flowers.",
            event_date=date.today(),
        )
        db.add(mem)
        await db.flush()

        import app.core.config
        synthetic_vector = create_synthetic_vector(0.85)

        with patch("app.ai.providers.embeddings.GeminiEmbeddingProvider.embed", return_value=synthetic_vector):
            with patch.object(app.core.config.get_settings(), "GOOGLE_API_KEY", "valid-test-key"):
                event = MemoryCreatedEvent(memory_id=mem.id, patient_id=patient.id)
                await handle_memory_created_generate_embedding(event, db_session=db)

        # Verify embedding was stored in DB
        res = await db.execute(select(MemoryEmbedding).where(MemoryEmbedding.memory_id == mem.id))
        emb = res.scalar_one_or_none()
        assert emb is not None
        assert list(emb.embedding) == synthetic_vector
        assert "Kamakhya temple" in emb.embedding_text

    @pytest.mark.asyncio
    async def test_embedding_failure_does_not_fail_memory_creation(
        self, db: AsyncSession, patient: Patient
    ):
        """If Gemini embedding API fails / times out, memory creation succeeds without raising."""
        import app.core.config

        mem = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.FAMILY_STORY,
            title="Old childhood stories in Shillong",
            description="Talking about rain and pine trees.",
            event_date=date.today(),
        )
        db.add(mem)
        await db.flush()

        with patch("app.ai.providers.embeddings.GeminiEmbeddingProvider.embed", side_effect=Exception("API Timeout")):
            with patch.object(app.core.config.get_settings(), "GOOGLE_API_KEY", "valid-test-key"):
                event = MemoryCreatedEvent(memory_id=mem.id, patient_id=patient.id)
                # Must not raise exception
                await handle_memory_created_generate_embedding(event, db_session=db)

        # Memory remains intact
        mem_check = await db.get(Memory, mem.id)
        assert mem_check is not None

    @pytest.mark.asyncio
    async def test_semantic_retrieval_finds_relevant_memory(
        self, db: AsyncSession, patient: Patient
    ):
        """Semantic search finds memory by cosine similarity matching."""
        vector_temple = [0.9] + [0.1] * 767
        vector_cooking = [0.1] + [0.9] * 767

        # Memory 1: Temple visit
        mem1 = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.OUTING,
            title="Temple outing with flowers",
            description="Offering flowers at the temple with family.",
            event_date=date.today(),
        )
        # Memory 2: Cooking mangoes
        mem2 = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.MEAL,
            title="Making sweet mango chutney",
            description="Cooking mango chutney in the kitchen.",
            event_date=date.today(),
        )
        db.add_all([mem1, mem2])
        await db.flush()

        # Add embeddings
        emb1 = MemoryEmbedding(memory_id=mem1.id, embedding=vector_temple, embedding_text=mem1.title)
        emb2 = MemoryEmbedding(memory_id=mem2.id, embedding=vector_cooking, embedding_text=mem2.title)
        db.add_all([emb1, emb2])
        await db.flush()

        retriever = SemanticRetriever(db)

        # Query biased towards temple vector
        with patch("app.ai.providers.embeddings.GeminiEmbeddingProvider.embed", return_value=vector_temple):
            matches = await retriever.search(patient.id, "Where did we take flowers?")

        assert len(matches) >= 1
        assert matches[0]["memory"].id == mem1.id
        assert matches[0]["similarity"] > 0.95

    @pytest.mark.asyncio
    async def test_semantic_retrieval_respects_threshold(
        self, db: AsyncSession, patient: Patient
    ):
        """Low similarity results below threshold are filtered out."""
        vector_a = [1.0] + [0.0] * 767
        vector_orthogonal = [0.0] + [1.0] + [0.0] * 766  # cosine similarity = 0.0

        mem = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.GENERAL,
            title="Doctor appointment",
            description="Routine checkup at clinic.",
            event_date=date.today(),
        )
        db.add(mem)
        await db.flush()
        db.add(MemoryEmbedding(memory_id=mem.id, embedding=vector_a, embedding_text=mem.title))
        await db.flush()

        retriever = SemanticRetriever(db)

        # Query with orthogonal vector (similarity = 0.0)
        with patch("app.ai.providers.embeddings.GeminiEmbeddingProvider.embed", return_value=vector_orthogonal):
            matches = await retriever.search(patient.id, "Playing tennis", threshold=0.65)

        assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_semantic_search_scoped_to_patient(
        self, db: AsyncSession, patient: Patient
    ):
        """Vectors from Patient A are never returned when querying for Patient B."""
        vector_shared = [0.8] + [0.2] * 767

        # Patient B
        other_user = User(
            id=uuid.uuid4(),
            email="other_patient@test.com",
            full_name="Other Patient",
            hashed_password="hash",
            role=UserRole.PATIENT,
        )
        db.add(other_user)
        await db.flush()
        patient_b = Patient(id=uuid.uuid4(), user_id=other_user.id)
        db.add(patient_b)
        await db.flush()

        # Memory belongs to Patient B
        mem_b = Memory(
            id=uuid.uuid4(),
            patient_id=patient_b.id,
            memory_type=MemoryType.VISIT,
            title="Secret family heirloom discussion",
            description="Patient B heirloom in Guwahati.",
            event_date=date.today(),
        )
        db.add(mem_b)
        await db.flush()
        db.add(MemoryEmbedding(memory_id=mem_b.id, embedding=vector_shared, embedding_text=mem_b.title))
        await db.flush()

        retriever = SemanticRetriever(db)

        # Search as Patient A (must NOT leak Patient B's memory)
        with patch("app.ai.providers.embeddings.GeminiEmbeddingProvider.embed", return_value=vector_shared):
            matches_a = await retriever.search(patient.id, "heirloom in Guwahati")

        assert len(matches_a) == 0

    @pytest.mark.asyncio
    async def test_hybrid_retrieval_ranks_significant_memory_higher(
        self, db: AsyncSession, patient: Patient
    ):
        """Significant pinned memories receive a composite ranking boost."""
        vector_base = [0.8] + [0.2] * 767

        # Memory 1: Normal memory with slightly higher raw similarity
        mem_normal = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.GENERAL,
            title="Had evening chai",
            description="Drank hot chai.",
            event_date=date.today(),
            is_significant=False,
        )
        # Memory 2: Highly significant memory
        mem_significant = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.VISIT,
            title="Granddaughter wedding celebration",
            description="Wonderful family gathering for wedding.",
            event_date=date.today(),
            is_significant=True,
        )
        db.add_all([mem_normal, mem_significant])
        await db.flush()

        db.add_all([
            MemoryEmbedding(memory_id=mem_normal.id, embedding=vector_base, embedding_text=mem_normal.title),
            MemoryEmbedding(memory_id=mem_significant.id, embedding=vector_base, embedding_text=mem_significant.title),
        ])
        await db.flush()

        retriever = SemanticRetriever(db)

        with patch("app.ai.providers.embeddings.GeminiEmbeddingProvider.embed", return_value=vector_base):
            matches = await retriever.search(patient.id, "celebration with family")

        assert len(matches) >= 2
        # Significant memory must be ranked #1 due to boost
        assert matches[0]["memory"].id == mem_significant.id
        assert matches[0]["score"] > matches[1]["score"]

    @pytest.mark.asyncio
    async def test_narrative_question_uses_semantic_memory(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, db: AsyncSession
    ):
        """Open-ended narrative questions ('Tell me about the mangoes we picked') retrieve semantic memory."""
        vector_mango = [0.85] + [0.15] * 767

        mem = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.FAMILY_STORY,
            title="Picking ripe Alphonsos in Ratnagiri",
            description="We picked golden Alphonsos with Rahul under the summer sun.",
            event_date=date(2025, 5, 10),
            is_significant=True,
        )
        db.add(mem)
        await db.flush()
        db.add(MemoryEmbedding(memory_id=mem.id, embedding=vector_mango, embedding_text=mem.title))
        await db.flush()

        with patch("app.ai.providers.embeddings.GeminiEmbeddingProvider.embed", return_value=vector_mango):
            resp = await client.post(
                f"/api/v1/patients/{patient.id}/conversations/message",
                headers=auth_headers,
                json={"query": "Tell me about the mangoes we picked"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["confidence"] >= 0.85
        assert "Alphonsos" in data["reply"] or "mango" in data["reply"].lower()
        assert any("Alphonsos" in s["title"] for s in data["sources"])
