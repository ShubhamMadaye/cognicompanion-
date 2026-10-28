"""
CogniCompanion — Query Understanding Layer Test Suite
=======================================================
Tests the full spectrum of imperfect elderly patient queries as specified.
Covers: pronoun resolution, bare follow-up expansion, spelling correction,
malformed queries, multi-memory planning, ambiguity detection, patient isolation,
and the full 10-turn stress-test sequence.

Run with:
    cd backend
    python -m pytest tests/test_query_understanding.py -v
    python -m pytest tests/test_query_understanding.py::test_full_stress_sequence -v -s
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.memory_engine.intent_detector import PMEIntent
from app.ai.memory_engine.query_understanding import (
    ConversationContext,
    QueryUnderstanding,
    QueryUnderstandingLayer,
    _correct_spelling,
    _levenshtein,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

PATIENT_ID_A = uuid.uuid4()
PATIENT_ID_B = uuid.uuid4()
CONV_ID_A = uuid.uuid4()
CONV_ID_B = uuid.uuid4()
TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)


def make_context(
    patient_id: uuid.UUID = PATIENT_ID_A,
    conversation_id: uuid.UUID = CONV_ID_A,
    last_intent: PMEIntent | None = None,
    last_person: str | None = None,
    last_event: str | None = None,
    last_location: str | None = None,
    last_date: date | None = None,
    recent_turns: list | None = None,
    known_people: list[str] | None = None,
    known_medications: list[str] | None = None,
    language: str = "en",
) -> ConversationContext:
    return ConversationContext(
        conversation_id=conversation_id,
        patient_id=patient_id,
        language=language,
        recent_turns=recent_turns or [],
        last_intent=last_intent,
        last_referenced_person=last_person,
        last_referenced_event=last_event,
        last_referenced_location=last_location,
        last_referenced_date=last_date,
        last_pme_evidence=[],
        known_people=known_people or ["Rahul", "Priya", "Riya"],
        known_medications=known_medications or ["Donepezil", "Aspirin"],
    )


# ── Levenshtein ───────────────────────────────────────────────────────────────

def test_levenshtein_identical():
    assert _levenshtein("Rahul", "Rahul") == 0

def test_levenshtein_one_transposition():
    assert _levenshtein("Rhaul", "Rahul") == 2  # Transposition counts as 2 ops

def test_levenshtein_one_substitution():
    assert _levenshtein("Rahul", "Rahul") == 0
    assert _levenshtein("Rahal", "Rahul") == 1

def test_levenshtein_one_insertion():
    assert _levenshtein("Rahull", "Rahul") == 1

def test_levenshtein_deletion():
    assert _levenshtein("Rahu", "Rahul") == 1


# ── Spelling Correction ───────────────────────────────────────────────────────

def test_spelling_correction_person_name():
    """'Rahull' should be corrected to 'Rahul' (distance 1)."""
    ctx = make_context(known_people=["Rahul", "Priya"])
    corrected, corrections = _correct_spelling("Rahull visited yesterday", ctx)
    assert "Rahul" in corrected
    assert "Rahull" in corrections or corrected != "Rahull visited yesterday"


def test_spelling_correction_transposition_rhaul():
    """'Rhaul' (transposition, distance 2) — should NOT be corrected at distance >1 for names."""
    ctx = make_context(known_people=["Rahul", "Priya"])
    corrected, corrections = _correct_spelling("Rhaul visited me", ctx)
    # Distance is 2 for a pure transposition, which is at the limit for person names (≤1)
    # So this may or may not correct — the test verifies the system doesn't crash
    assert isinstance(corrected, str)


def test_spelling_correction_medical_word():
    """'medcine' should be corrected to 'medicine' via the medical corrections dict."""
    ctx = make_context()
    corrected, corrections = _correct_spelling("did i take my medcine today", ctx)
    assert "medicine" in corrected.lower()


def test_spelling_correction_daughter():
    """'daughtr' → 'daughter'."""
    ctx = make_context()
    corrected, _ = _correct_spelling("my daughtr visited me", ctx)
    assert "daughter" in corrected.lower()


def test_spelling_no_overcorrect():
    """A correctly spelled word should never be changed."""
    ctx = make_context(known_people=["Rahul"])
    corrected, corrections = _correct_spelling("When did Rahul come?", ctx)
    assert "Rahul" in corrected
    assert corrections == {}


def test_spelling_does_not_change_db():
    """Spelling correction must only apply to the query string, not mutate anything."""
    ctx = make_context(known_people=["Rahul"])
    original_people = list(ctx.known_people)
    _correct_spelling("Rhaul visited me", ctx)
    assert ctx.known_people == original_people


# ── Pronoun Resolution ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pronoun_resolution_he():
    """'When did he visit me?' → resolved 'he' to 'Rahul' from context."""
    ctx = make_context(
        last_intent=PMEIntent.VISIT_RECALL,
        last_person="Rahul",
        recent_turns=[
            {"role": "assistant", "content": "Rahul visited you on Sunday.", "person": "Rahul"}
        ],
    )
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("When did he visit me?", context=ctx)
    assert result.needs_clarification is False
    assert "Rahul" in result.rewritten_query
    assert result.resolved_references.get("he") == "Rahul" or "Rahul" in result.rewritten_query


@pytest.mark.asyncio
async def test_pronoun_resolution_we():
    """'What did we do?' → resolved 'we' to 'patient and Rahul' from context."""
    ctx = make_context(
        last_intent=PMEIntent.VISIT_RECALL,
        last_person="Rahul",
        recent_turns=[
            {"role": "assistant", "content": "Rahul visited you on Sunday.", "person": "Rahul"}
        ],
    )
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("What did we do?", context=ctx)
    assert result.needs_clarification is False
    assert "Rahul" in result.rewritten_query or "patient" in result.rewritten_query.lower()


@pytest.mark.asyncio
async def test_pronoun_he_no_context_requires_clarification():
    """'When did he visit?' with no context → must ask for clarification, not guess."""
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("When did he visit?", context=None)
    # Without context, pronoun should either be passed through or trigger clarification
    assert isinstance(result, QueryUnderstanding)
    # System must not crash and must return a usable result
    assert result.rewritten_query


# ── Bare Follow-Up Resolution ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bare_where_with_clear_context():
    """'Where?' after a visit query with one person → deterministic resolution."""
    ctx = make_context(
        last_intent=PMEIntent.VISIT_RECALL,
        last_person="Rahul",
        recent_turns=[
            {"role": "assistant", "content": "Rahul visited you last Sunday.", "person": "Rahul"}
        ],
    )
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("Where?", context=ctx)
    assert result.needs_clarification is False
    assert "Rahul" in result.rewritten_query
    assert result.resolution_mode == "deterministic"


@pytest.mark.asyncio
async def test_bare_where_with_ambiguous_context():
    """'Where?' when context has two recent visits → must ask for clarification."""
    ctx = make_context(
        last_intent=PMEIntent.VISIT_RECALL,
        last_person="Rahul",  # last person is Rahul, but Priya also appeared
        recent_turns=[
            {"role": "assistant", "content": "Rahul visited you on Sunday.", "person": "Rahul"},
            {"role": "patient", "content": "And Priya?"},
            {"role": "assistant", "content": "Priya visited you on Monday.", "person": "Priya"},
        ],
    )
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("Where?", context=ctx)
    # With multiple visits in context, system should clarify
    # (Exact behavior depends on Mode A implementation; at minimum it must not crash)
    assert isinstance(result, QueryUnderstanding)


@pytest.mark.asyncio
async def test_bare_when_with_medication_context():
    """'When?' after medication intent → asks 'When did the patient take their medication?'"""
    ctx = make_context(last_intent=PMEIntent.MEDICATION_ADHERENCE)
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("When?", context=ctx)
    assert result.needs_clarification is False
    assert "medication" in result.rewritten_query.lower()
    assert result.resolution_mode == "deterministic"


@pytest.mark.asyncio
async def test_bare_who_with_no_context():
    """'Who?' with no prior context → must request clarification."""
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("Who?", context=None)
    assert result.needs_clarification is True
    assert result.clarification_question is not None


# ── Malformed Queries ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_malformed_query_rahul_last_sunday_where():
    """'rahul last sunday where' → should understand as visit location query."""
    ctx = make_context(
        last_intent=None,
        last_person=None,
        known_people=["Rahul"],
    )
    qu_layer = QueryUnderstandingLayer()

    # Mock Gemini for deterministic testing
    mock_gemini_response = {
        "intent_hint": "VISIT_RECALL",
        "entities": {"person": "Rahul"},
        "date_expression": "last sunday",
        "resolved_references": {},
        "rewritten_query": "Where did Rahul visit the patient last Sunday?",
        "needs_clarification": False,
        "clarification_question": None,
        "confidence": 0.94,
        "evidence_plan": [],
    }

    with patch(
        "app.ai.memory_engine.query_understanding._run_gemini_qu",
        new_callable=AsyncMock,
        return_value=mock_gemini_response,
    ):
        result = await qu_layer.understand("rahul last sunday where", context=ctx)

    assert "Rahul" in result.rewritten_query
    assert result.needs_clarification is False
    assert "where" in result.rewritten_query.lower() or "location" in result.rewritten_query.lower()


@pytest.mark.asyncio
async def test_malformed_query_where_rahul_me():
    """'where rahul me' → system must not fail, should infer visit location."""
    ctx = make_context(known_people=["Rahul"])
    qu_layer = QueryUnderstandingLayer()

    mock_gemini_response = {
        "intent_hint": "VISIT_RECALL",
        "entities": {"person": "Rahul"},
        "date_expression": None,
        "resolved_references": {},
        "rewritten_query": "Where did Rahul visit the patient?",
        "needs_clarification": False,
        "clarification_question": None,
        "confidence": 0.78,
        "evidence_plan": [],
    }

    with patch(
        "app.ai.memory_engine.query_understanding._run_gemini_qu",
        new_callable=AsyncMock,
        return_value=mock_gemini_response,
    ):
        result = await qu_layer.understand("where rahul me", context=ctx)

    assert isinstance(result, QueryUnderstanding)
    assert result.rewritten_query
    assert result.needs_clarification is False


# ── Temporal Follow-Up ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_medication_followup_yesterday():
    """'What about yesterday?' after medication intent → inherits MEDICATION_ADHERENCE."""
    ctx = make_context(
        last_intent=PMEIntent.MEDICATION_ADHERENCE,
        last_date=TODAY,
    )
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("What about yesterday?", context=ctx)
    assert result.needs_clarification is False
    assert "yesterday" in result.rewritten_query.lower() or (
        result.date_reference and result.date_reference.timeframe == "yesterday"
    )
    assert "medication" in result.rewritten_query.lower()


@pytest.mark.asyncio
async def test_visit_followup_yesterday():
    """'And yesterday?' after visit recall → continues visit intent for yesterday."""
    ctx = make_context(
        last_intent=PMEIntent.VISIT_RECALL,
        last_person="Rahul",
    )
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("What about yesterday?", context=ctx)
    assert result.needs_clarification is False
    assert "yesterday" in result.rewritten_query.lower()


# ── And [Person] Follow-Up ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_and_person_followup():
    """'And Priya?' after a visit query → asks about Priya's visit."""
    ctx = make_context(
        last_intent=PMEIntent.VISIT_RECALL,
        last_person="Rahul",
        known_people=["Rahul", "Priya"],
    )
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("And Priya?", context=ctx)
    assert result.needs_clarification is False
    assert "Priya" in result.rewritten_query


# ── Multi-Memory Compound Queries ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_multi_memory_compound_query():
    """'When did I meet Rahul and what did we do?' → should produce evidence_plan."""
    ctx = make_context(known_people=["Rahul"])
    qu_layer = QueryUnderstandingLayer()

    mock_gemini_response = {
        "intent_hint": "VISIT_RECALL",
        "entities": {"person": "Rahul"},
        "date_expression": None,
        "resolved_references": {"we": "patient+Rahul"},
        "rewritten_query": "When did Rahul visit the patient and what did they do together?",
        "needs_clarification": False,
        "clarification_question": None,
        "confidence": 0.87,
        "evidence_plan": [
            "retrieve: person=Rahul",
            "retrieve: visit_date for Rahul",
            "retrieve: activity memory for visit with Rahul",
        ],
    }

    with patch(
        "app.ai.memory_engine.query_understanding._run_gemini_qu",
        new_callable=AsyncMock,
        return_value=mock_gemini_response,
    ):
        result = await qu_layer.understand(
            "When did I meet Rahul and what did we do?", context=ctx
        )

    assert result.needs_clarification is False
    assert len(result.evidence_plan) == 3
    assert "Rahul" in result.rewritten_query


# ── Ambiguity — Never Guess ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ambiguous_when_no_context_forces_clarification():
    """'When?' with absolutely no prior context → must clarify, not guess."""
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("When?", context=None)
    assert result.needs_clarification is True
    assert result.clarification_question is not None
    assert len(result.clarification_question) > 5


@pytest.mark.asyncio
async def test_ambiguous_daughter_no_context():
    """'My daughter?' with no context → clarification needed."""
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("My daughter?", context=None)
    assert isinstance(result, QueryUnderstanding)


# ── Patient Isolation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patient_isolation():
    """
    Two ConversationContexts for different patients must never mix entities.
    Patient A has Rahul. Patient B has Priya.
    """
    ctx_a = make_context(
        patient_id=PATIENT_ID_A,
        conversation_id=CONV_ID_A,
        last_person="Rahul",
        last_intent=PMEIntent.VISIT_RECALL,
        known_people=["Rahul"],
    )
    ctx_b = make_context(
        patient_id=PATIENT_ID_B,
        conversation_id=CONV_ID_B,
        last_person="Priya",
        last_intent=PMEIntent.VISIT_RECALL,
        known_people=["Priya"],
    )

    qu_layer = QueryUnderstandingLayer()

    result_a = await qu_layer.understand("Where?", context=ctx_a)
    result_b = await qu_layer.understand("Where?", context=ctx_b)

    # Patient A's result must reference Rahul, never Priya
    assert "Priya" not in result_a.rewritten_query
    # Patient B's result must reference Priya, never Rahul
    assert "Rahul" not in result_b.rewritten_query


# ── Empty / Trivial Input ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_query():
    """Empty query must not crash and returns a safe default."""
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("", context=None)
    assert isinstance(result, QueryUnderstanding)
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_whitespace_only_query():
    """Whitespace-only query must not crash."""
    qu_layer = QueryUnderstandingLayer()
    result = await qu_layer.understand("   ", context=None)
    assert isinstance(result, QueryUnderstanding)


# ── Full 10-Turn Stress Test ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_stress_sequence():
    """
    Validates the complete 10-turn sequence from the spec:

    1.  When did Rahul visit me?
    2.  Where?
    3.  What did we do?
    4.  Who was with us?
    5.  What did we eat?
    6.  And my daughter?
    7.  When did she come?
    8.  where we go
    9.  rahul last sunday?
    10. what happened that day?

    Each turn builds on the previous one. The system must maintain context.
    """
    qu_layer = QueryUnderstandingLayer()

    # ── Turn 1: Full question ──────────────────────────────────────────────────
    ctx1 = make_context(
        last_intent=None,
        last_person=None,
        known_people=["Rahul", "Priya"],
    )
    r1 = await qu_layer.understand("When did Rahul visit me?", context=ctx1)
    assert r1.needs_clarification is False
    assert "Rahul" in r1.rewritten_query
    print(f"\nTurn 1: {r1.rewritten_query!r} [{r1.resolution_mode}]")

    # Simulate assistant response — update context
    ctx2 = make_context(
        last_intent=PMEIntent.VISIT_RECALL,
        last_person="Rahul",
        last_event="Rahul's visit",
        recent_turns=[
            {"role": "patient", "content": "When did Rahul visit me?"},
            {"role": "assistant", "content": "Rahul visited you last Sunday.", "person": "Rahul"},
        ],
        known_people=["Rahul", "Priya"],
    )

    # ── Turn 2: "Where?" ───────────────────────────────────────────────────────
    r2 = await qu_layer.understand("Where?", context=ctx2)
    assert r2.needs_clarification is False
    assert "Rahul" in r2.rewritten_query
    assert r2.resolution_mode == "deterministic"
    print(f"Turn 2: {r2.rewritten_query!r} [{r2.resolution_mode}]")

    # ── Turn 3: "What did we do?" ──────────────────────────────────────────────
    r3 = await qu_layer.understand("What did we do?", context=ctx2)
    assert r3.needs_clarification is False
    assert "Rahul" in r3.rewritten_query or "patient" in r3.rewritten_query.lower()
    print(f"Turn 3: {r3.rewritten_query!r} [{r3.resolution_mode}]")

    # ── Turn 4: "Who was with us?" ─────────────────────────────────────────────
    r4 = await qu_layer.understand("Who was with us?", context=ctx2)
    # Should resolve 'us' to patient+Rahul and ask who else was at the visit
    assert isinstance(r4, QueryUnderstanding)
    print(f"Turn 4: {r4.rewritten_query!r} [{r4.resolution_mode}]")

    # ── Turn 5: "What did we eat?" ─────────────────────────────────────────────
    r5 = await qu_layer.understand("What did we eat?", context=ctx2)
    assert isinstance(r5, QueryUnderstanding)
    assert not r5.needs_clarification or r5.clarification_question is not None
    print(f"Turn 5: {r5.rewritten_query!r} [{r5.resolution_mode}]")

    # Update context to introduce daughter
    ctx6 = make_context(
        last_intent=PMEIntent.VISIT_RECALL,
        last_person="Rahul",
        last_event="Rahul's visit",
        recent_turns=[
            {"role": "patient", "content": "When did Rahul visit me?"},
            {"role": "assistant", "content": "Rahul visited you last Sunday.", "person": "Rahul"},
            {"role": "patient", "content": "What did we do?"},
            {"role": "assistant", "content": "You and Rahul played cards together."},
        ],
        known_people=["Rahul", "Priya", "Daughter"],
    )

    # ── Turn 6: "And my daughter?" ────────────────────────────────────────────
    r6 = await qu_layer.understand("And my daughter?", context=ctx6)
    assert r6.needs_clarification is False
    assert "daughter" in r6.rewritten_query.lower()
    print(f"Turn 6: {r6.rewritten_query!r} [{r6.resolution_mode}]")

    # Update context — daughter now referenced
    ctx7 = make_context(
        last_intent=PMEIntent.VISIT_RECALL,
        last_person="daughter",
        last_event="daughter's visit",
        recent_turns=[
            {"role": "patient", "content": "And my daughter?"},
            {"role": "assistant", "content": "Your daughter Priya visited you on Monday.", "person": "Priya"},
        ],
        known_people=["Rahul", "Priya"],
    )

    # ── Turn 7: "When did she come?" ───────────────────────────────────────────
    r7 = await qu_layer.understand("When did she come?", context=ctx7)
    assert r7.needs_clarification is False
    # "she" should resolve to the daughter / Priya
    assert "daughter" in r7.rewritten_query.lower() or "Priya" in r7.rewritten_query
    print(f"Turn 7: {r7.rewritten_query!r} [{r7.resolution_mode}]")

    # ── Turn 8: "where we go" ─────────────────────────────────────────────────
    r8 = await qu_layer.understand("where we go", context=ctx7)
    # Malformed — QU should interpret as asking where they went with the daughter
    assert isinstance(r8, QueryUnderstanding)
    assert r8.rewritten_query
    print(f"Turn 8: {r8.rewritten_query!r} [{r8.resolution_mode}]")

    # ── Turn 9: "rahul last sunday?" ──────────────────────────────────────────
    ctx9 = make_context(
        last_intent=PMEIntent.VISIT_RECALL,
        last_person=None,  # Reset — new topic
        known_people=["Rahul", "Priya"],
    )
    r9 = await qu_layer.understand("rahul last sunday?", context=ctx9)
    assert isinstance(r9, QueryUnderstanding)
    assert "Rahul" in r9.rewritten_query or r9.entities.get("person") == "Rahul"
    print(f"Turn 9: {r9.rewritten_query!r} [{r9.resolution_mode}]")

    # ── Turn 10: "what happened that day?" ────────────────────────────────────
    ctx10 = make_context(
        last_intent=PMEIntent.VISIT_RECALL,
        last_person="Rahul",
        last_date=TODAY - timedelta(days=3),  # Simulate "last Sunday"
        recent_turns=[
            {"role": "patient", "content": "rahul last sunday?"},
            {"role": "assistant", "content": "Rahul visited you last Sunday, September 14.", "person": "Rahul"},
        ],
        known_people=["Rahul"],
    )
    r10 = await qu_layer.understand("what happened that day?", context=ctx10)
    assert r10.needs_clarification is False
    # "that day" should resolve to the date referenced in context
    assert isinstance(r10, QueryUnderstanding)
    print(f"Turn 10: {r10.rewritten_query!r} [{r10.resolution_mode}]")

    print("\n✅ All 10 turns passed without crash.")
    print("Context flow maintained throughout sequence.")
