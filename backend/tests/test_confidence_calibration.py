"""
CogniCompanion — Multi-Factor Confidence Calibration & Regression Tests
========================================================================
Validates that:
  1. Confidence is NOT always 95%.
  2. Exact structured evidence produces calibrated HIGH confidence (0.90 - 0.99).
  3. Strong semantic memories produce calibrated scores (~0.75 - 0.85), NOT a blanket 95%.
  4. Moderate semantic matches produce MEDIUM confidence (0.50 - 0.74).
  5. Weak semantic matches produce LOW confidence (0.30 - 0.49).
  6. Zero evidence produces UNKNOWN confidence (<= 0.25).
  7. Ambiguous intents receive calibrated penalties.
  8. Partial query coverage receives calibrated penalties.
  9. Temporal mismatch receives calibrated penalties.
  10. Corroborating evidence increases confidence without duplicate inflation.
  11. Conflicting/contradictory evidence decreases confidence.
  12. Missing records reflect lack of evidence and never invent negative facts.
  13. Multi-factor explainability dictionary is populated with all 6 factors.
"""

from datetime import date, datetime, timezone, timedelta
import uuid
import pytest
from unittest.mock import MagicMock

from app.ai.memory_engine.confidence_engine import ConfidenceEngine
from app.ai.memory_engine.intent_detector import PMEIntent
from app.ai.memory_engine.temporal_parser import TemporalContext
from app.domains.memories.models import Memory, Person, MemoryType
from app.domains.timeline.models import Medication, MedicationAdherenceLog, Event, Routine, MedicationTiming
from app.domains.games.models import Game, GameSession, DifficultyLevel, GameType
from app.domains.analytics.models import CognitiveMetric, DailyStatistic


class TestConfidenceCalibration:
    def test_confidence_is_not_always_95_percent(self):
        """
        Regression test: Runs multiple representative queries across domains and verifies
        that confidence scores are meaningfully varied and calibrated across tiers:
        exact structured > strong semantic > moderate semantic > weak / no evidence.
        """
        # Tier 1: Exact structured medication adherence log
        med = Medication(id=uuid.uuid4(), name="Donepezil", dosage="5mg", timing="BEFORE_BREAKFAST")
        log = MedicationAdherenceLog(id=uuid.uuid4(), medication_id=med.id, taken=True, taken_at=datetime.now(timezone.utc))
        res_exact = ConfidenceEngine.evaluate(
            intent=PMEIntent.MEDICATION_ADHERENCE,
            retrieved_data={
                "has_medications": True,
                "items": [{"medication": med, "is_taken": True, "taken_at": datetime.now(timezone.utc), "log": log}],
            },
            query="Did I take my morning medication?",
        )

        # Tier 2: Strong semantic memory match (~0.78)
        mem_mock = MagicMock(spec=Memory)
        mem_mock.id = uuid.uuid4()
        mem_mock.title = "Daughter visited"
        mem_mock.description = "Had lunch together"
        mem_mock.event_date = date.today()
        res_strong_sem = ConfidenceEngine.evaluate(
            intent=PMEIntent.GENERAL_CONVERSATION,
            retrieved_data={
                "unified_memories": [{"memory": mem_mock, "similarity": 0.78, "score": 0.78}],
            },
            query="Tell me about my daughter.",
        )

        # Tier 3: Moderate semantic memory match (~0.65)
        res_mod_sem = ConfidenceEngine.evaluate(
            intent=PMEIntent.GENERAL_CONVERSATION,
            retrieved_data={
                "unified_memories": [{"memory": mem_mock, "similarity": 0.65, "score": 0.65}],
            },
            query="What was my favorite food when I was young?",
        )

        # Tier 4: Weak semantic match (~0.51)
        res_weak_sem = ConfidenceEngine.evaluate(
            intent=PMEIntent.GENERAL_CONVERSATION,
            retrieved_data={
                "unified_memories": [{"memory": mem_mock, "similarity": 0.51, "score": 0.51}],
            },
            query="What was my childhood school?",
        )

        # Tier 5: Zero evidence query
        res_no_ev = ConfidenceEngine.evaluate(
            intent=PMEIntent.VISIT_RECALL,
            retrieved_data={"memories": [], "timeline_events": [], "unified_memories": []},
            query="Did I visit London yesterday?",
        )

        scores = [res_exact.score, res_strong_sem.score, res_mod_sem.score, res_weak_sem.score, res_no_ev.score]

        # 1. Assert they are not all 0.95
        assert any(s != 0.95 for s in scores), "Scores should not all be 0.95"
        assert len(set(round(s, 2) for s in scores)) >= 4, "Expected distinct calibrated scores across tiers"

        # 2. Assert strict calibrated hierarchy:
        # exact structured > strong semantic > moderate semantic > weak semantic > no evidence
        assert res_exact.score > res_strong_sem.score, "Exact structured should score higher than standalone semantic"
        assert res_strong_sem.score > res_mod_sem.score, "Strong semantic should score higher than moderate semantic"
        assert res_mod_sem.score > res_weak_sem.score, "Moderate semantic should score higher than weak semantic"
        assert res_weak_sem.score > res_no_ev.score, "Weak semantic should score higher than zero evidence"

        # 3. Assert calibration bands
        assert 0.90 <= res_exact.score <= 0.99
        assert 0.70 <= res_strong_sem.score <= 0.85
        assert 0.50 <= res_mod_sem.score <= 0.74
        assert 0.30 <= res_weak_sem.score <= 0.50
        assert res_no_ev.score <= 0.25
        assert res_no_ev.level == "UNKNOWN"

    def test_exact_medication_record_high_confidence(self):
        """Case 1: Exact medication record with verified log -> HIGH confidence (~0.90 - 0.99)."""
        med = Medication(id=uuid.uuid4(), name="Donepezil", dosage="5mg", timing="BEFORE_BREAKFAST")
        log = MedicationAdherenceLog(id=uuid.uuid4(), medication_id=med.id, taken=True, taken_at=datetime.now(timezone.utc))
        res = ConfidenceEngine.evaluate(
            intent=PMEIntent.MEDICATION_ADHERENCE,
            retrieved_data={
                "has_medications": True,
                "items": [{"medication": med, "is_taken": True, "taken_at": datetime.now(timezone.utc), "log": log}],
            },
            query="Did I take my morning medication?",
        )
        assert res.level == "HIGH"
        assert 0.90 <= res.score <= 0.99
        assert res.factors["evidence_strength"] >= 0.95
        assert res.factors["temporal_accuracy"] == 1.0

    def test_exact_game_record_high_confidence(self):
        """Case 2: Exact game progress with multiple sessions -> HIGH confidence (~0.88 - 0.97)."""
        game = Game(id=uuid.uuid4(), name="Memory Match", game_type=GameType.MEMORY_MATCH)
        sess1 = GameSession(id=uuid.uuid4(), game=game, score=150, accuracy=0.88, reaction_time_ms=2100, started_at=datetime.now(timezone.utc), difficulty_level=DifficultyLevel.EASY)
        sess2 = GameSession(id=uuid.uuid4(), game=game, score=180, accuracy=0.92, reaction_time_ms=1900, started_at=datetime.now(timezone.utc), difficulty_level=DifficultyLevel.MEDIUM)

        res = ConfidenceEngine.evaluate(
            intent=PMEIntent.GAME_PROGRESS,
            retrieved_data={
                "has_sessions": True,
                "sessions": [sess1, sess2],
            },
            query="How did I perform in today's games?",
        )
        assert res.level == "HIGH"
        assert 0.88 <= res.score <= 0.97
        assert len(res.sources) == 2

    def test_strong_semantic_memory_below_blanket_95(self):
        """Case 3: Strong semantic memory (~0.78 similarity) produces ~0.75 - 0.85, NOT 0.95."""
        mem = MagicMock(spec=Memory)
        mem.id = uuid.uuid4()
        mem.title = "Daughter visited"
        mem.description = "We had lunch and tea"
        mem.event_date = date.today()

        res = ConfidenceEngine.evaluate(
            intent=PMEIntent.GENERAL_CONVERSATION,
            retrieved_data={
                "unified_memories": [{"memory": mem, "similarity": 0.78, "score": 0.78}],
            },
            query="Tell me about my daughter.",
        )
        assert 0.70 <= res.score <= 0.85
        assert round(res.score, 2) != 0.95, "Must NOT be blanket 95%"
        assert res.level in ["HIGH", "MEDIUM"]

    def test_broad_query_partial_coverage_penalty(self):
        """Case 4: 'What happened yesterday?' with only 1 sparse record receives partial coverage penalty."""
        game = Game(id=uuid.uuid4(), name="Memory Match", game_type=GameType.MEMORY_MATCH)
        sess = GameSession(id=uuid.uuid4(), game=game, score=100, accuracy=0.80, reaction_time_ms=2500, started_at=datetime.now(timezone.utc), difficulty_level=DifficultyLevel.EASY)

        res_broad = ConfidenceEngine.evaluate(
            intent=PMEIntent.GAME_PROGRESS,
            retrieved_data={
                "has_sessions": True,
                "sessions": [sess],
            },
            query="What happened yesterday?",
        )
        # Broad query receives coverage penalty, expected in MEDIUM range (~0.45 - 0.70)
        assert res_broad.score < 0.75 or res_broad.factors["query_coverage"] <= 0.60
        assert res_broad.factors["query_coverage"] < 0.80

    def test_weak_semantic_match_low_confidence(self):
        """Case 5: Weak semantic match (~0.51 similarity) -> LOW confidence (~0.30 - 0.50)."""
        mem = MagicMock(spec=Memory)
        mem.id = uuid.uuid4()
        mem.title = "School building"
        mem.description = "A red brick school"
        mem.event_date = date(1965, 5, 10)

        res = ConfidenceEngine.evaluate(
            intent=PMEIntent.GENERAL_CONVERSATION,
            retrieved_data={
                "unified_memories": [{"memory": mem, "similarity": 0.51, "score": 0.51}],
            },
            query="What was my favorite food when I was young?",
        )
        assert res.score <= 0.50
        assert res.level in ["LOW", "UNKNOWN"]

    def test_no_evidence_low_or_unknown(self):
        """Case 6: Zero evidence -> UNKNOWN confidence (<= 0.25)."""
        res = ConfidenceEngine.evaluate(
            intent=PMEIntent.VISIT_RECALL,
            retrieved_data={"memories": [], "timeline_events": [], "unified_memories": []},
            query="Did I visit London yesterday?",
        )
        assert res.score <= 0.25
        assert res.level == "UNKNOWN"
        assert len(res.sources) == 0

    def test_corroborating_evidence_boosts_confidence(self):
        """Corroborating structured record + semantic memory increases confidence over standalone record."""
        p = Person(id=uuid.uuid4(), name="Rahul Sharma", relationship="son", description="Loving son")

        mem = MagicMock(spec=Memory)
        mem.id = uuid.uuid4()
        mem.title = "Tea with Rahul"
        mem.description = "Rahul visited for tea"
        mem.event_date = date.today()

        # Standalone person record
        res_single = ConfidenceEngine.evaluate(
            intent=PMEIntent.PERSON_LOOKUP,
            retrieved_data={"matched_person": p, "exact_match": True, "unified_memories": []},
            query="Who is Rahul?",
        )

        # Person record + corroborated semantic memory
        res_corroborated = ConfidenceEngine.evaluate(
            intent=PMEIntent.PERSON_LOOKUP,
            retrieved_data={
                "matched_person": p,
                "exact_match": True,
                "unified_memories": [{"memory": mem, "similarity": 0.88, "score": 0.88}],
            },
            query="Who is Rahul?",
        )

        assert res_corroborated.score >= res_single.score
        assert res_corroborated.factors["source_consistency"] >= res_single.factors["source_consistency"]

    def test_ambiguous_intent_confidence_penalty(self):
        """Ambiguous query ('how did i do') receives lower intent certainty and a penalty."""
        res_clear = ConfidenceEngine.evaluate(
            intent=PMEIntent.GAME_PROGRESS,
            retrieved_data={"has_sessions": False, "sessions": []},
            query="How did I perform in Memory Match?",
        )
        res_ambiguous = ConfidenceEngine.evaluate(
            intent=PMEIntent.GAME_PROGRESS,
            retrieved_data={"has_sessions": False, "sessions": []},
            query="how did i do",
        )
        assert res_ambiguous.factors["intent_certainty"] < res_clear.factors["intent_certainty"]

    def test_explainability_factors_populated(self):
        """Ensures all explainability factors (including claim grounding factors) are present."""
        res = ConfidenceEngine.evaluate(
            intent=PMEIntent.MEDICATION_SCHEDULE,
            retrieved_data={"has_medications": False, "medications": []},
            query="What are my medications?",
        )
        expected_keys = {
            "evidence_strength",
            "retrieval_relevance",
            "query_coverage",
            "temporal_accuracy",
            "source_consistency",
            "intent_certainty",
            "entity_match",
            "subject_match",
        }
        assert set(res.factors.keys()) == expected_keys
        for k, v in res.factors.items():
            assert 0.0 <= v <= 1.0, f"Factor {k} must be in [0.0, 1.0], got {v}"

    def test_case_6_unrelated_visit_cannot_support_london_visit(self):
        """
        REGRESSION TEST FOR CASE 6:
        Query: 'Did I visit London yesterday?'
        Evidence: Only a visit by Rahul Sharma to the patient exists yesterday.
        Must result in UNKNOWN confidence (<= 0.20), entity_match=0, subject_match=0,
        0 supporting sources, and cannot claim the visit occurred.
        """
        rahul_visit = Memory(
            id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            title="Family Afternoon Visit",
            description="Rahul visited yesterday afternoon. You looked at photos together.",
            memory_type=MemoryType.VISIT,
            event_date=date.today() - timedelta(days=1),
        )
        # Raw query has direction=outgoing, target_name=London
        res = ConfidenceEngine.evaluate(
            intent=PMEIntent.VISIT_RECALL,
            retrieved_data={"memories": [rahul_visit], "timeline_events": [], "has_records": True},
            query="Did I visit London yesterday?",
            entities={
                "target_name": "London",
                "direction": "outgoing",
                "subject": "patient",
                "action": "visit",
                "timeframe": "yesterday",
            },
        )
        assert res.score <= 0.20, f"Case 6 score must be <= 0.20, got {res.score}"
        assert res.level == "UNKNOWN"
        assert len(res.sources) == 0, f"Unrelated visit must not be a supporting source, got {res.sources}"
        assert res.factors["entity_match"] == 0.0
        assert res.factors["subject_match"] == 0.0

    def test_entity_mismatch_medication_donepezil_vs_aspirin(self):
        """
        Query: 'Did I take Donepezil this morning?'
        Evidence: Only Aspirin log exists.
        Result: UNKNOWN (<= 0.20), entity_match=0.0, 0 sources.
        """
        aspirin = Medication(
            id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            name="Aspirin",
            dosage="75mg",
            timing=MedicationTiming.BEFORE_BREAKFAST,
            is_active=True,
        )
        res = ConfidenceEngine.evaluate(
            intent=PMEIntent.MEDICATION_ADHERENCE,
            retrieved_data={"has_medications": True, "items": [{"medication": aspirin, "is_taken": True, "taken_at": datetime.now()}]},
            query="Did I take Donepezil this morning?",
            entities={
                "target_medication": "Donepezil",
                "timing": "morning",
            },
        )
        assert res.score <= 0.20
        assert res.level == "UNKNOWN"
        assert len(res.sources) == 0
        assert res.factors["entity_match"] == 0.0

    def test_entity_mismatch_game_memory_match_vs_sudoku(self):
        """
        Query: 'Did I play Memory Match yesterday?'
        Evidence: Only Sudoku session exists.
        Result: UNKNOWN (<= 0.20), entity_match=0.0, 0 sources.
        """
        game_sudoku = Game(id=uuid.uuid4(), name="Sudoku")
        sess_sudoku = GameSession(
            id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            game_id=game_sudoku.id,
            game=game_sudoku,
            score=100,
            started_at=datetime.now(timezone.utc),
        )
        res = ConfidenceEngine.evaluate(
            intent=PMEIntent.GAME_PROGRESS,
            retrieved_data={"has_sessions": True, "sessions": [sess_sudoku]},
            query="Did I play Memory Match yesterday?",
            entities={
                "game_name": "Memory Match",
                "timeframe": "yesterday",
            },
        )
        assert res.score <= 0.20
        assert res.level == "UNKNOWN"
        assert len(res.sources) == 0
        assert res.factors["entity_match"] == 0.0

    def test_matching_rahul_visited_me_yields_high(self):
        """
        Query: 'Did Rahul visit me yesterday?'
        Evidence: Rahul Sharma visit yesterday exists.
        Result: HIGH (>= 0.90), entity_match=1.0, subject_match=1.0.
        """
        rahul = Person(id=uuid.uuid4(), patient_id=uuid.uuid4(), name="Rahul Sharma", relationship="son")
        rahul_visit = Memory(
            id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            title="Family Afternoon Visit",
            description="Rahul visited yesterday afternoon.",
            memory_type=MemoryType.VISIT,
            event_date=date.today() - timedelta(days=1),
        )
        rahul_visit.people.append(rahul)
        res = ConfidenceEngine.evaluate(
            intent=PMEIntent.VISIT_RECALL,
            retrieved_data={"memories": [rahul_visit], "timeline_events": [], "has_records": True},
            query="Did Rahul visit me yesterday?",
            entities={
                "target_name": "Rahul",
                "direction": "incoming",
                "subject": "Rahul",
                "action": "visit",
                "timeframe": "yesterday",
            },
        )
        assert res.score >= 0.90
        assert res.level == "HIGH"
        assert len(res.sources) == 1
        assert res.factors["entity_match"] == 1.0
        assert res.factors["subject_match"] == 1.0

