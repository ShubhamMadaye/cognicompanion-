"""
CogniCompanion — Personalized Memory Engine (PME) Central Orchestrator
=======================================================================
Coordinates the end-to-end grounded memory pipeline:
  1. Intent & Entity Detection (Query Preprocessing)
  2. Dual Retrieval (Intent-Aware Structured DB + Semantic Vector Search)
  3. Hybrid Ranking & Evidence Deduplication
  4. Context & Fallback Assembly
  5. Evidence-Quality Confidence & Source Attribution
  6. Grounded Response Generation (Configured Gemini LLM / Deterministic Fallback)
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory_engine.confidence_engine import ConfidenceEngine
from app.ai.memory_engine.context_builder import ContextBuilder
from app.ai.memory_engine.hybrid_ranker import HybridRanker
from app.ai.memory_engine.intent_detector import PMEIntent, detect_intent
from app.ai.memory_engine.query_understanding import (
    ConversationContext,
    QueryUnderstanding,
    QueryUnderstandingLayer,
    get_query_understanding_layer,
)
from app.ai.memory_engine.response_generator import ResponseGenerator
from app.ai.memory_engine.semantic_retriever import SemanticRetriever
from app.ai.memory_engine.structured_retriever import StructuredRetriever
from app.domains.voice.schemas import GroundedSource


@dataclass
class PMEResult:
    query: str
    intent: PMEIntent
    answer: str
    confidence_score: float
    confidence_level: str
    sources: list[GroundedSource] = field(default_factory=list)
    model_used: str | None = None
    entities: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    confidence_factors: dict[str, float] = field(default_factory=dict)
    # Query Understanding result — internal; optionally surfaced to caregiver dashboard
    query_understanding: QueryUnderstanding | None = None

    @property
    def reply(self) -> str:
        """Backward compatibility alias for answer."""
        return self.answer


class MemoryEngine:
    """
    Central orchestrator for the Personalized Memory Engine.
    Coordinates specialized components without duplicating their logic.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self.structured_retriever = StructuredRetriever(db)
        self.semantic_retriever = SemanticRetriever(db)

    async def process_query(
        self,
        patient_id: uuid.UUID,
        query: str,
        patient_name: str = "the patient",
        reference_date: date | None = None,
        language_code: str = "en",
        image_base64: str | None = None,
        conversation_context: ConversationContext | None = None,
    ) -> PMEResult:
        """
        Executes complete grounded retrieval and response generation for a patient query.
        The raw query is first processed by the Query Understanding Layer before retrieval.
        """
        # ── 0. Query Understanding (NEW) ──────────────────────────────────────
        # Handles: spelling correction, pronoun resolution, bare follow-up expansion,
        # coreference from conversation context, ambiguity detection, query rewriting.
        qu_layer = get_query_understanding_layer()
        qu = await qu_layer.understand(
            raw_query=query,
            context=conversation_context,
            patient_name=patient_name,
            reference_date=reference_date,
        )

        # Short-circuit: if QU requests clarification, return it immediately
        # without running PME retrieval. Clarification is a grounded response
        # (confidence=1.0 because it is a definite question, not a hallucination).
        if qu.needs_clarification and qu.clarification_question:
            return PMEResult(
                query=query,
                intent=PMEIntent.GENERAL_CONVERSATION,
                answer=qu.clarification_question,
                confidence_score=1.0,
                confidence_level="HIGH",
                sources=[],
                model_used="clarification-engine",
                entities={},
                context={},
                confidence_factors={},
                query_understanding=qu,
            )

        # Use rewritten query for all downstream processing
        effective_query = qu.rewritten_query if qu.rewritten_query.strip() else query

        # 1. Intent & Entity Detection (now operates on the rewritten query)
        intent, entities = detect_intent(
            effective_query,
            reference_date=reference_date,
            conversation_context=conversation_context,
        )
        temporal = entities.get("temporal")

        # 2. Intent-Specific Structured Retrieval
        structured_data: dict[str, Any] = {}
        if intent == PMEIntent.PERSON_LOOKUP:
            structured_data = await self.structured_retriever.retrieve_person(
                patient_id=patient_id,
                name_hint=entities.get("target_name"),
            )
        elif intent == PMEIntent.VISIT_RECALL:
            structured_data = await self.structured_retriever.retrieve_visit_memories(
                patient_id=patient_id,
                timeframe=entities.get("timeframe"),
                target_name=entities.get("target_name"),
                reference_date=reference_date,
                temporal=temporal,
                direction=entities.get("direction"),
            )
        elif intent == PMEIntent.MEDICATION_ADHERENCE:
            structured_data = await self.structured_retriever.retrieve_medication_adherence(
                patient_id=patient_id,
                target_date=temporal.start_date if (temporal and temporal.start_date) else reference_date,
                timing_hint=entities.get("timing"),
                med_name_hint=entities.get("target_medication"),
            )
        elif intent == PMEIntent.MEDICATION_SCHEDULE:
            structured_data = await self.structured_retriever.retrieve_medication_schedule(
                patient_id=patient_id,
                timing_hint=entities.get("timing"),
            )
        elif intent == PMEIntent.GAME_PROGRESS:
            structured_data = await self.structured_retriever.retrieve_game_progress(
                patient_id=patient_id,
                temporal=temporal,
                game_name=entities.get("game_name"),
            )
        elif intent == PMEIntent.COGNITIVE_PROGRESS:
            structured_data = await self.structured_retriever.retrieve_cognitive_progress(
                patient_id=patient_id,
                temporal=temporal,
            )
        elif intent == PMEIntent.EVENT_LOOKUP:
            structured_data = await self.structured_retriever.retrieve_events(
                patient_id=patient_id,
                temporal=temporal,
            )
        elif intent == PMEIntent.TEMPORAL_RECALL:
            structured_data = await self.structured_retriever.retrieve_temporal_recall(
                patient_id=patient_id,
                target_date=temporal.start_date if (temporal and temporal.start_date) else reference_date,
                temporal=temporal,
            )
        elif intent == PMEIntent.DAILY_ROUTINE:
            structured_data = await self.structured_retriever.retrieve_daily_routine(
                patient_id=patient_id,
                target_date=temporal.start_date if (temporal and temporal.start_date) else reference_date,
                time_of_day=entities.get("time_of_day"),
            )

        # 2.5 Always fetch background overview for comprehensive grounding across all queries
        overview = await self.structured_retriever.retrieve_patient_overview(patient_id)
        if "all_known_people" not in structured_data or not structured_data["all_known_people"]:
            structured_data["all_known_people"] = overview["all_known_people"]
        if "medications" not in structured_data or not structured_data["medications"]:
            structured_data["medications"] = overview["medications"]
        if "routines" not in structured_data or not structured_data["routines"]:
            structured_data["routines"] = overview["routines"]

        # 3. Semantic Vector Search (Strictly patient-scoped)
        # Uses the rewritten query from QU for better semantic similarity
        semantic_matches = await self.semantic_retriever.search(
            patient_id=patient_id,
            query=effective_query,
        )

        # 4. Hybrid Ranking & Evidence Deduplication
        retrieved_data = HybridRanker.rank_and_deduplicate(
            intent=intent,
            structured_data=structured_data,
            semantic_matches=semantic_matches,
        )

        # 5. Deterministic Confidence & Source Attribution
        conf_res = ConfidenceEngine.evaluate(
            intent=intent,
            retrieved_data=retrieved_data,
            query=effective_query,
            entities=entities,
            reference_date=reference_date,
        )
        confidence_score = conf_res.score
        confidence_level = conf_res.level
        sources = conf_res.sources
        confidence_factors = conf_res.factors

        # 6. Grounded Context & System Instruction Assembly
        context = ContextBuilder.build_context(
            intent=intent,
            retrieved_data=retrieved_data,
            patient_name=patient_name,
            language_code=language_code,
        )

        # 7. Dual-Mode Response Generation (Configured Gemini LLM / Deterministic Fallback)
        answer_text, model_used = await ResponseGenerator.generate_response(
            query=effective_query,
            intent=intent,
            context=context,
            confidence_level=confidence_level,
            image_base64=image_base64,
        )

        return PMEResult(
            query=query,
            intent=intent,
            answer=answer_text,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            sources=sources,
            model_used=model_used,
            entities=entities,
            context=context,
            confidence_factors=confidence_factors,
            query_understanding=qu,
        )

