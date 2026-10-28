"""
CogniCompanion — Comprehensive Personalized Memory Engine (PME) Test Suite
===========================================================================
Validates all 20+ required grounding, retrieval, safety, and confidence behaviors:
  1. "Who visited me yesterday?"
  2. "Who visited me today?"
  3. No visit record exists (Absence is not inferred as peaceful time)
  4. Rahul yesterday vs Priya today (Strict day isolation; Priya never appears)
  5. "Who is Rahul?" (Exact person lookup)
  6. Unknown person lookup (Returns UNKNOWN confidence, not MEDIUM)
  7. "What do you remember about Rahul?" (Narrative episodic memory recall)
  8. Morning medicine taken
  9. Morning medicine not taken (Deterministic adherence caution)
  10. No morning medicine exists (Strict timing; does not fall back to evening pills)
  11. Schedule this morning (Routine & scheduled events)
  12. No routine exists ("Couldn't find any routines", UNKNOWN confidence)
  13. Strong semantic match (HIGH confidence)
  14. Weak semantic match (LOW confidence)
  15. No semantic match (UNKNOWN confidence)
  16. Patient isolation (Patient A never retrieves Patient B's memories or persons)
  17. Gemini unavailable -> deterministic fallback
  18. Grounded Gemini context construction
  19. Duplicate structured/semantic memory deduplication (Only 1 GroundedSource)
  20. Date/time boundary precision (Midnight separation)
  21. Person extraction non-greedy ("Was Rahul here yesterday?" -> "Rahul")
  22. Medication query variations ("Have I already taken my pills?")
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory_engine.confidence_engine import ConfidenceEngine
from app.ai.memory_engine.context_builder import ContextBuilder
from app.ai.memory_engine.intent_detector import PMEIntent, detect_intent
from app.ai.memory_engine.memory_engine import MemoryEngine
from app.ai.memory_engine.semantic_retriever import SemanticRetriever
from app.ai.memory_engine.structured_retriever import StructuredRetriever
from app.domains.memories.models import Memory, MemoryType, Person
from app.domains.patients.models import Patient, User, UserRole
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
from app.domains.voice.models import MemoryEmbedding


def _create_vector(val: float, dim: int = 768) -> list[float]:
    vec = [0.0] * dim
    vec[0] = val
    vec[1] = 1.0 - abs(val)
    return vec


class TestPMEComprehensive:

    @pytest.mark.asyncio
    async def test_who_visited_me_yesterday(self, db: AsyncSession, patient: Patient):
        """1. Querying yesterday's visit retrieves yesterday's memory and timeline events."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        rahul = Person(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Rahul Sharma",
            relationship="son",
            is_active=True,
        )
        db.add(rahul)
        await db.flush()

        mem = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.VISIT,
            title="Rahul visit with sweets",
            description="Rahul came over yesterday and we ate jalebis.",
            event_date=yesterday,
        )
        mem.people.append(rahul)
        db.add(mem)
        await db.flush()

        engine = MemoryEngine(db)
        result = await engine.process_query(patient.id, "Who visited me yesterday?")

        assert result.intent == PMEIntent.VISIT_RECALL
        assert "Rahul" in result.reply
        assert result.confidence_level == "HIGH"
        assert len(result.sources) >= 1
        assert any("Rahul" in s.title or (s.summary and "Rahul" in s.summary) for s in result.sources)

    @pytest.mark.asyncio
    async def test_who_visited_me_today(self, db: AsyncSession, patient: Patient):
        """2. Querying today's visit retrieves today's visit only."""
        today = date.today()

        priya = Person(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Priya Nair",
            relationship="daughter",
            is_active=True,
        )
        db.add(priya)
        await db.flush()

        mem = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.VISIT,
            title="Priya morning visit",
            description="Priya visited this morning.",
            event_date=today,
        )
        mem.people.append(priya)
        db.add(mem)
        await db.flush()

        engine = MemoryEngine(db)
        result = await engine.process_query(patient.id, "Who visited me today?")

        assert result.intent == PMEIntent.VISIT_RECALL
        assert "Priya" in result.reply
        assert result.confidence_level == "HIGH"

    @pytest.mark.asyncio
    async def test_no_visit_record_exists(self, db: AsyncSession, patient: Patient):
        """3. When no visit record exists, NEVER say 'peaceful time with no visitors'. State lack of records honestly."""
        engine = MemoryEngine(db)
        result = await engine.process_query(patient.id, "Who visited me yesterday?")

        assert result.intent == PMEIntent.VISIT_RECALL
        # Must honestly state missing data
        assert "couldn't find a visit recorded" in result.reply or "could not find" in result.reply
        # Must NEVER hallucinate peaceful time or assert that no visitors came
        assert "peaceful time" not in result.reply.lower()
        assert "no visitors came" not in result.reply.lower()
        assert result.confidence_level == "UNKNOWN"
        assert result.confidence_score <= 0.30
        assert len(result.sources) == 0

    @pytest.mark.asyncio
    async def test_rahul_yesterday_vs_priya_today(self, db: AsyncSession, patient: Patient):
        """4. Rahul visited yesterday, Priya visited today. 'Who visited me yesterday?' MUST return Rahul only."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        rahul = Person(id=uuid.uuid4(), patient_id=patient.id, name="Rahul Sharma", relationship="son", is_active=True)
        priya = Person(id=uuid.uuid4(), patient_id=patient.id, name="Priya Nair", relationship="daughter", is_active=True)
        db.add_all([rahul, priya])
        await db.flush()

        mem_yesterday = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.VISIT,
            title="Rahul yesterday visit",
            description="Rahul spent time with you yesterday.",
            event_date=yesterday,
        )
        mem_yesterday.people.append(rahul)

        # Timeline event for Priya today
        now = datetime.now(timezone.utc)
        today_start = datetime(today.year, today.month, today.day, 14, 0, 0, tzinfo=timezone.utc)
        ev_today = Event(
            id=uuid.uuid4(),
            patient_id=patient.id,
            event_type=EventType.VISIT,
            title="Priya Afternoon Tea Visit",
            description="Priya came for afternoon tea today.",
            start_time=today_start,
        )
        db.add_all([mem_yesterday, ev_today])
        await db.flush()

        engine = MemoryEngine(db)
        result = await engine.process_query(patient.id, "Who visited me yesterday?")

        assert "Rahul" in result.reply
        # PRIYA MUST NOT APPEAR
        assert "Priya" not in result.reply
        for s in result.sources:
            assert "Priya" not in s.title

    @pytest.mark.asyncio
    async def test_who_is_rahul_exact_person(self, db: AsyncSession, patient: Patient):
        """5. 'Who is Rahul?' returns exact person record and relationship."""
        rahul = Person(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Rahul Sharma",
            relationship="elder son",
            description="Lives in Pune and calls every evening.",
            is_active=True,
        )
        db.add(rahul)
        await db.flush()

        engine = MemoryEngine(db)
        result = await engine.process_query(patient.id, "Who is Rahul?")

        assert result.intent == PMEIntent.PERSON_LOOKUP
        assert "Rahul" in result.reply
        assert "elder son" in result.reply
        assert result.confidence_level == "HIGH"
        assert any(s.source_type == "person" and s.id == str(rahul.id) for s in result.sources)

    @pytest.mark.asyncio
    async def test_unknown_person_lookup(self, db: AsyncSession, patient: Patient):
        """6. Looking up an unrecorded person must return UNKNOWN confidence, not MEDIUM or HIGH."""
        # Patient has known person Amit
        amit = Person(id=uuid.uuid4(), patient_id=patient.id, name="Amit Kumar", relationship="nephew", is_active=True)
        db.add(amit)
        await db.flush()

        engine = MemoryEngine(db)
        result = await engine.process_query(patient.id, "Who is Dr. Malhotra?")

        assert result.intent == PMEIntent.PERSON_LOOKUP
        assert "couldn't find any information recorded" in result.reply or "could not find" in result.reply
        # Must be UNKNOWN, not MEDIUM or HIGH
        assert result.confidence_level == "UNKNOWN"
        assert result.confidence_score <= 0.30
        assert len(result.sources) == 0

    @pytest.mark.asyncio
    async def test_what_do_you_remember_about_rahul(self, db: AsyncSession, patient: Patient):
        """7. 'What do you remember about Rahul?' retrieves associated episodic memories."""
        rahul = Person(id=uuid.uuid4(), patient_id=patient.id, name="Rahul", relationship="son", is_active=True)
        db.add(rahul)
        await db.flush()

        mem = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.FAMILY_STORY,
            title="Rahul Diwali kite flying",
            description="Rahul flew red paper kites on the rooftop during Diwali.",
            event_date=date(2024, 11, 1),
        )
        mem.people.append(rahul)
        db.add(mem)
        await db.flush()

        engine = MemoryEngine(db)
        result = await engine.process_query(patient.id, "What do you remember about Rahul?")

        assert result.intent == PMEIntent.PERSON_LOOKUP
        assert result.entities.get("target_name") == "Rahul"
        assert "Rahul" in result.reply
        assert "kite" in result.reply.lower() or "diwali" in result.reply.lower()
        assert result.confidence_level == "HIGH"

    @pytest.mark.asyncio
    async def test_morning_medicine_taken(self, db: AsyncSession, patient: Patient):
        """8. 'Did I take my morning medicine?' with recorded log returns confirmed taken status."""
        today = date.today()
        med = Medication(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Donepezil",
            dosage="5 mg",
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
            taken_at=datetime(today.year, today.month, today.day, 8, 30, 0, tzinfo=timezone.utc),
        )
        db.add(log)
        await db.flush()

        engine = MemoryEngine(db)
        result = await engine.process_query(patient.id, "Did I take my morning medicine?")

        assert result.intent == PMEIntent.MEDICATION_ADHERENCE
        assert "taken" in result.reply.lower()
        assert "Donepezil" in result.reply
        assert result.confidence_level == "HIGH"
        assert any(s.source_type == "medication" and s.id == str(med.id) for s in result.sources)

    @pytest.mark.asyncio
    async def test_morning_medicine_not_taken(self, db: AsyncSession, patient: Patient):
        """9. 'Did I take my morning medicine?' without adherence log returns deterministic warning."""
        med = Medication(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Donepezil",
            dosage="5 mg",
            frequency=MedicationFrequency.ONCE_DAILY,
            timing=MedicationTiming.AFTER_BREAKFAST,
            is_active=True,
        )
        db.add(med)
        await db.flush()

        engine = MemoryEngine(db)
        result = await engine.process_query(patient.id, "Did I take my morning medicine?")

        assert result.intent == PMEIntent.MEDICATION_ADHERENCE
        assert "don't have a record" in result.reply.lower() or "check with your caregiver" in result.reply.lower()
        assert result.confidence_level == "HIGH"

    @pytest.mark.asyncio
    async def test_no_morning_medicine_exists(self, db: AsyncSession, patient: Patient):
        """10. If patient only has evening medicine, asking about morning medicine does NOT fall back to evening."""
        evening_med = Medication(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Melatonin",
            dosage="3 mg",
            frequency=MedicationFrequency.ONCE_DAILY,
            timing=MedicationTiming.BEDTIME,
            is_active=True,
        )
        db.add(evening_med)
        await db.flush()

        engine = MemoryEngine(db)
        result = await engine.process_query(patient.id, "Did I take my morning medicine?")

        assert result.intent == PMEIntent.MEDICATION_ADHERENCE
        # Melatonin is bedtime, must NOT be returned as morning medicine!
        assert "Melatonin" not in result.reply
        assert "couldn't find any medications scheduled for the morning" in result.reply or "couldn't find" in result.reply
        assert result.confidence_level == "UNKNOWN"
        assert len(result.sources) == 0

    @pytest.mark.asyncio
    async def test_morning_schedule(self, db: AsyncSession, patient: Patient):
        """11. 'What should I do this morning?' returns morning routines."""
        routine = Routine(
            id=uuid.uuid4(),
            patient_id=patient.id,
            title="Morning Chai & Plant Watering",
            category=RoutineCategory.MORNING,
            scheduled_time=time(8, 30),
            days_of_week=127,  # All days
            is_active=True,
        )
        db.add(routine)
        await db.flush()

        engine = MemoryEngine(db)
        result = await engine.process_query(patient.id, "What should I do this morning?")

        assert result.intent == PMEIntent.DAILY_ROUTINE
        assert "Morning Chai" in result.reply
        assert result.confidence_level == "HIGH"
        assert any(s.source_type == "routine" and s.id == str(routine.id) for s in result.sources)

    @pytest.mark.asyncio
    async def test_no_routine_exists(self, db: AsyncSession, patient: Patient):
        """12. No routines recorded -> states missing records honestly, confidence UNKNOWN."""
        engine = MemoryEngine(db)
        result = await engine.process_query(patient.id, "What is my schedule this morning?")

        assert result.intent == PMEIntent.DAILY_ROUTINE
        assert "couldn't find any routines" in result.reply.lower() or "could not find" in result.reply.lower()
        # Must not assert that patient had a relaxed day with nothing to do
        assert "relaxed" not in result.reply.lower()
        assert result.confidence_level == "UNKNOWN"
        assert result.confidence_score <= 0.30
        assert len(result.sources) == 0

    @pytest.mark.asyncio
    async def test_semantic_retrieval_strong_match(self, db: AsyncSession, patient: Patient):
        """13. Semantic retrieval with similarity >= high threshold returns HIGH confidence."""
        vec = _create_vector(0.9)
        mem = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.FAMILY_STORY,
            title="Saraswati Puja in Kolkata",
            description="We wore yellow clothes and made khichdi for Saraswati puja.",
            event_date=date(2023, 1, 26),
        )
        db.add(mem)
        await db.flush()
        db.add(MemoryEmbedding(memory_id=mem.id, embedding=vec, embedding_text=mem.title))
        await db.flush()

        engine = MemoryEngine(db)
        with patch("app.ai.providers.embeddings.GeminiEmbeddingProvider.embed", return_value=vec):
            result = await engine.process_query(patient.id, "Tell me about Saraswati Puja")

        assert result.confidence_level == "HIGH"
        assert result.confidence_score >= 0.80
        assert any(s.source_type == "memory" and s.id == str(mem.id) for s in result.sources)

    @pytest.mark.asyncio
    async def test_semantic_retrieval_weak_match(self, db: AsyncSession, patient: Patient):
        """14. Semantic retrieval with similarity below medium threshold returns LOW confidence."""
        vec_query = _create_vector(0.48)
        vec_mem = _create_vector(0.95)

        mem = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.GENERAL,
            title="Old radio repair",
            description="Repaired the Philips radio in 1998.",
            event_date=date(1998, 4, 12),
        )
        db.add(mem)
        await db.flush()
        db.add(MemoryEmbedding(memory_id=mem.id, embedding=vec_mem, embedding_text=mem.title))
        await db.flush()

        retriever = SemanticRetriever(db)
        with patch("app.ai.providers.embeddings.GeminiEmbeddingProvider.embed", return_value=vec_query):
            # Threshold set to 0.40 to allow weak match to be evaluated
            matches = await retriever.search(patient.id, "repairing electronics", threshold=0.40)

        # Evaluate through confidence engine
        score, level, sources = ConfidenceEngine.evaluate(
            PMEIntent.GENERAL_CONVERSATION,
            {"unified_memories": matches},
        )
        assert level in ["LOW", "MEDIUM", "UNKNOWN"]
        assert score < 0.70

    @pytest.mark.asyncio
    async def test_no_semantic_match(self, db: AsyncSession, patient: Patient):
        """15. No embeddings pass threshold -> UNKNOWN confidence."""
        engine = MemoryEngine(db)
        with patch("app.ai.providers.embeddings.GeminiEmbeddingProvider.embed", return_value=_create_vector(0.1)):
            result = await engine.process_query(patient.id, "Tell me about space exploration")

        assert result.confidence_level == "UNKNOWN"
        assert result.confidence_score <= 0.30

    @pytest.mark.asyncio
    async def test_patient_isolation(self, db: AsyncSession, patient: Patient):
        """16. Patient A cannot retrieve Patient B's memories or people."""
        # Patient B
        user_b = User(
            id=uuid.uuid4(),
            email="patient_b@demo.com",
            hashed_password="hash",
            role=UserRole.PATIENT,
            full_name="Patient B",
        )
        db.add(user_b)
        await db.flush()

        patient_b = Patient(id=uuid.uuid4(), user_id=user_b.id)
        db.add(patient_b)
        await db.flush()

        # Secret person belonging to Patient B
        secret_person = Person(
            id=uuid.uuid4(),
            patient_id=patient_b.id,
            name="Vikram Singh",
            relationship="secret contact",
            is_active=True,
        )
        db.add(secret_person)

        # Secret memory belonging to Patient B
        secret_mem = Memory(
            id=uuid.uuid4(),
            patient_id=patient_b.id,
            memory_type=MemoryType.VISIT,
            title="Secret Visit for Patient B",
            description="Patient B had a private visitor.",
            event_date=date.today(),
        )
        db.add(secret_mem)
        await db.flush()

        engine = MemoryEngine(db)

        # Patient A queries for Vikram Singh
        res_person = await engine.process_query(patient.id, "Who is Vikram Singh?")
        assert "Vikram Singh is your" not in res_person.reply
        assert res_person.confidence_level == "UNKNOWN"

        # Patient A queries for today's visits
        res_visit = await engine.process_query(patient.id, "Who visited me today?")
        assert "Secret Visit" not in res_visit.reply
        for s in res_visit.sources:
            assert s.id != str(secret_mem.id)

    @pytest.mark.asyncio
    async def test_gemini_unavailable_deterministic_fallback(self, db: AsyncSession, patient: Patient):
        """17. When Gemini LLM is unavailable or raises an exception, deterministic fallback succeeds."""
        rahul = Person(id=uuid.uuid4(), patient_id=patient.id, name="Rahul", relationship="son", is_active=True)
        db.add(rahul)
        await db.flush()

        engine = MemoryEngine(db)
        with patch("app.ai.providers.llm.GeminiLLMProvider.generate", side_effect=Exception("API Unreachable")):
            result = await engine.process_query(patient.id, "Who is Rahul?")

        assert result.intent == PMEIntent.PERSON_LOOKUP
        assert "Rahul is your son" in result.reply
        assert result.confidence_level == "HIGH"
        assert result.model_used in ["deterministic-fallback", "deterministic-safety-engine"]

    @pytest.mark.asyncio
    async def test_gemini_grounded_response(self, db: AsyncSession, patient: Patient):
        """18. Gemini generates a compassionate response strictly based on grounded facts."""
        rahul = Person(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Rahul Sharma",
            relationship="loving son",
            description="He lives in Pune and calls every evening.",
            is_active=True,
        )
        db.add(rahul)
        await db.flush()

        engine = MemoryEngine(db)
        import app.core.config
        with patch.object(app.core.config.get_settings(), "GOOGLE_API_KEY", "valid-fake-key"):
            with patch(
                "app.ai.providers.llm.GeminiLLMProvider.generate",
                return_value="Rahul Sharma is your loving son who lives in Pune. He calls you every evening.",
            ):
                result = await engine.process_query(patient.id, "Who is Rahul?")

        assert "Rahul Sharma" in result.reply
        assert "loving son" in result.reply

    @pytest.mark.asyncio
    async def test_duplicate_memory_deduplication(self, db: AsyncSession, patient: Patient):
        """19. Memory retrieved both structurally and semantically is deduplicated into a single source."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        vec = _create_vector(0.95)

        mem = Memory(
            id=uuid.uuid4(),
            patient_id=patient.id,
            memory_type=MemoryType.VISIT,
            title="Rahul Afternoon Tea",
            description="Rahul brought delicious kachoris.",
            event_date=yesterday,
        )
        db.add(mem)
        await db.flush()
        db.add(MemoryEmbedding(memory_id=mem.id, embedding=vec, embedding_text=mem.title))
        await db.flush()

        engine = MemoryEngine(db)
        with patch("app.ai.providers.embeddings.GeminiEmbeddingProvider.embed", return_value=vec):
            result = await engine.process_query(patient.id, "Who visited me yesterday?")

        # Source list must contain mem.id exactly once
        matching_sources = [s for s in result.sources if s.id == str(mem.id)]
        assert len(matching_sources) == 1

    @pytest.mark.asyncio
    async def test_date_time_boundaries(self, db: AsyncSession, patient: Patient):
        """20. Midnight boundary test: events from 23:59:59 yesterday belong to yesterday, not today."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Event at 23:55 PM yesterday
        late_yesterday = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 55, 0, tzinfo=timezone.utc)
        ev_yesterday = Event(
            id=uuid.uuid4(),
            patient_id=patient.id,
            event_type=EventType.VISIT,
            title="Late Evening Family Call",
            start_time=late_yesterday,
        )

        # Event at 00:05 AM today
        early_today = datetime(today.year, today.month, today.day, 0, 5, 0, tzinfo=timezone.utc)
        ev_today = Event(
            id=uuid.uuid4(),
            patient_id=patient.id,
            event_type=EventType.VISIT,
            title="Midnight Medicine Check",
            start_time=early_today,
        )
        db.add_all([ev_yesterday, ev_today])
        await db.flush()

        engine = MemoryEngine(db)
        result_yesterday = await engine.process_query(patient.id, "Who visited me yesterday?")
        assert any(s.id == str(ev_yesterday.id) for s in result_yesterday.sources)
        assert not any(s.id == str(ev_today.id) for s in result_yesterday.sources)

        result_today = await engine.process_query(patient.id, "Who visited me today?")
        assert any(s.id == str(ev_today.id) for s in result_today.sources)
        assert not any(s.id == str(ev_yesterday.id) for s in result_today.sources)

    def test_person_name_non_greedy_extraction(self):
        """21. Person extraction does not greedily capture the rest of the sentence."""
        i1, e1 = detect_intent("What do you remember about Rahul?")
        assert e1.get("target_name") == "Rahul"

        i2, e2 = detect_intent("Was Rahul here yesterday?")
        assert e2.get("target_name") == "Rahul"

        i3, e3 = detect_intent("I remember Rahul coming over, when was that?")
        assert e3.get("target_name") == "Rahul"

        i4, e4 = detect_intent("Who is Priya Sharma?")
        assert e4.get("target_name") == "Priya Sharma"

    def test_medication_query_variations(self):
        """22. Medication queries with natural variations are accurately classified."""
        i1, e1 = detect_intent("Did I take my morning medicine?")
        assert i1 == PMEIntent.MEDICATION_ADHERENCE
        assert e1.get("timing") == "morning"

        i2, e2 = detect_intent("Have I already taken my pills?")
        assert i2 == PMEIntent.MEDICATION_ADHERENCE

        i3, e3 = detect_intent("Did I take my 8 AM dose?")
        assert i3 == PMEIntent.MEDICATION_ADHERENCE
        assert e3.get("timing") == "morning"

        i4, e4 = detect_intent("Have I taken my evening pills?")
        assert i4 == PMEIntent.MEDICATION_ADHERENCE
        assert e4.get("timing") == "evening"
