"""
CogniCompanion — Extended PME & Assistant Response Contract Tests
===================================================================
Validates the new native capabilities:
  1. GAME_PROGRESS intent & temporal retrieval (scores, accuracy, reaction time, mistakes)
  2. COGNITIVE_PROGRESS intent, CPI trend, and clinical assistive disclaimer
  3. MEDICATION_SCHEDULE vs MEDICATION_ADHERENCE distinction
  4. EVENT_LOOKUP intent & upcoming events calendar
  5. Central temporal parser bounds (today, yesterday, this week, last week)
  6. Non-inference on missing data ("I couldn't find any recorded...", never "You didn't play")
  7. Typed Assistant Response Contract (answer, reply alias, confidence_info, sources, grounded)
"""

from datetime import date, datetime, time, timedelta, timezone
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory_engine.intent_detector import PMEIntent, detect_intent
from app.ai.memory_engine.memory_engine import MemoryEngine
from app.ai.memory_engine.temporal_parser import parse_temporal_context
from app.domains.analytics.models import CognitiveMetric, DailyStatistic
from app.domains.games.models import DifficultyLevel, Game, GameSession, GameType, SessionStatus
from app.domains.patients.models import Patient
from app.domains.timeline.models import (
    Event,
    EventType,
    Medication,
    MedicationAdherenceLog,
    MedicationFrequency,
    MedicationTiming,
)


@pytest.mark.asyncio
class TestPMEExtended:

    async def test_temporal_parser_bounds(self):
        """Validates that temporal parser extracts exact date ranges."""
        ref = date(2026, 9, 20)

        ctx_today = parse_temporal_context("How did I do today?", reference_date=ref)
        assert ctx_today.timeframe == "today"
        assert ctx_today.start_date == ref
        assert ctx_today.end_date == ref

        ctx_yesterday = parse_temporal_context("What games did I play yesterday?", reference_date=ref)
        assert ctx_yesterday.timeframe == "yesterday"
        assert ctx_yesterday.start_date == ref - timedelta(days=1)
        assert ctx_yesterday.end_date == ref - timedelta(days=1)

        ctx_morning = parse_temporal_context("What medicines do I take in the morning?", reference_date=ref)
        assert ctx_morning.timing == "morning"

        ctx_week = parse_temporal_context("How was my progress this week?", reference_date=ref)
        assert ctx_week.timeframe == "this_week"
        assert ctx_week.start_date == ref - timedelta(days=7)

    async def test_medication_schedule_vs_adherence_distinction(self, db: AsyncSession, patient: Patient):
        """Distinguishes between schedule query ('What medicines do I take?') and adherence query ('Did I take it?')."""
        med = Medication(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Donepezil",
            dosage="5 mg",
            frequency=MedicationFrequency.ONCE_DAILY,
            timing=MedicationTiming.BEFORE_BREAKFAST,
            is_active=True,
        )
        db.add(med)
        await db.flush()

        engine = MemoryEngine(db)

        # 1. Schedule query
        sched_res = await engine.process_query(patient.id, "What medicines do I take in the morning?")
        assert sched_res.intent == PMEIntent.MEDICATION_SCHEDULE
        assert "Donepezil" in sched_res.answer
        assert sched_res.confidence_level == "HIGH"
        assert any(s.source_type == "medication" and s.id == str(med.id) for s in sched_res.sources)

        # 2. Adherence query
        adh_res = await engine.process_query(patient.id, "Did I take my morning medicine?")
        assert adh_res.intent == PMEIntent.MEDICATION_ADHERENCE
        assert "don't have a record" in adh_res.answer.lower()

    async def test_game_progress_retrieval_and_non_inference(self, db: AsyncSession, patient: Patient):
        """Validates GAME_PROGRESS retrieval and non-inference when no sessions exist."""
        today = date.today()

        game = Game(
            id=uuid.uuid4(),
            game_type=GameType.MEMORY_MATCH,
            name="Memory Match",
            description="Card pair matching",
        )
        db.add(game)
        await db.flush()

        session = GameSession(
            id=uuid.uuid4(),
            patient_id=patient.id,
            game_id=game.id,
            status=SessionStatus.COMPLETED,
            difficulty_level=DifficultyLevel.EASY,
            score=150,
            accuracy=0.86,
            reaction_time_ms=2400,
            mistakes=2,
            started_at=datetime(today.year, today.month, today.day, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(today.year, today.month, today.day, 10, 3, 0, tzinfo=timezone.utc),
            duration_seconds=180,
        )
        db.add(session)
        await db.flush()

        engine = MemoryEngine(db)

        # Query today's games -> found
        res_today = await engine.process_query(patient.id, "How did I perform in today's games?")
        assert res_today.intent == PMEIntent.GAME_PROGRESS
        assert res_today.confidence_level == "HIGH"
        assert "86%" in res_today.answer
        assert any(s.source_type == "game_session" for s in res_today.sources)
        assert res_today.answer == res_today.reply  # Verify alias

        # Query yesterday's games -> NONE exist. Non-inference check!
        res_yesterday = await engine.process_query(patient.id, "What games did I play yesterday?")
        assert res_yesterday.intent == PMEIntent.GAME_PROGRESS
        assert "couldn't find any recorded game sessions" in res_yesterday.answer.lower()
        # MUST NEVER say "You didn't play any games"
        assert "you didn't play" not in res_yesterday.answer.lower()

    async def test_cognitive_progress_cpi_and_assistive_disclaimer(self, db: AsyncSession, patient: Patient):
        """Validates COGNITIVE_PROGRESS intent, CPI trend calculation, and clinical assistive disclaimer."""
        today = date.today()

        metric = CognitiveMetric(
            id=uuid.uuid4(),
            patient_id=patient.id,
            metric_date=today,
            memory_accuracy=0.85,
            reaction_performance=0.80,
            completion_rate=0.90,
            engagement_score=0.88,
            cpi_score=84.0,
            cpi_delta=2.5,
        )
        db.add(metric)
        await db.flush()

        engine = MemoryEngine(db)
        res = await engine.process_query(patient.id, "Am I getting better?")

        assert res.intent == PMEIntent.COGNITIVE_PROGRESS
        assert res.confidence_level == "HIGH"
        assert "84" in res.answer
        # MUST contain assistive disclaimer
        assert "assistive progress indicator" in res.answer.lower() or "not a medical diagnosis" in res.answer.lower()
        assert any(s.source_type == "cognitive_metric" for s in res.sources)

    async def test_event_lookup_calendar(self, db: AsyncSession, patient: Patient):
        """Validates EVENT_LOOKUP intent and upcoming calendar appointments."""
        now = datetime.now(timezone.utc)
        appointment = Event(
            id=uuid.uuid4(),
            patient_id=patient.id,
            event_type=EventType.APPOINTMENT,
            title="Dr. Sen Neurologist Consultation",
            description="Routine cognitive checkup",
            location="City Memory Clinic",
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=1),
        )
        db.add(appointment)
        await db.flush()

        engine = MemoryEngine(db)
        res = await engine.process_query(patient.id, "What appointments do I have?")

        assert res.intent == PMEIntent.EVENT_LOOKUP
        assert res.confidence_level == "HIGH"
        assert "Dr. Sen" in res.answer
        assert any(s.source_type == "event" and s.id == str(appointment.id) for s in res.sources)
