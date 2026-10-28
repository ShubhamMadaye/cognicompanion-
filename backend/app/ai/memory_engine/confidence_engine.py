"""
CogniCompanion — PME Evidence-Based Confidence Engine
=====================================================
Calculates deterministic, calibrated multi-factor confidence scoring and builds
explicit, deduplicated GroundedSource lists based on patient evidence.

DESIGN PRINCIPLES:
  1. Evidence quality, NOT model fluency:
     Confidence represents how strongly patient-specific database evidence
     supports the generated answer. It does NOT represent LLM fluency.
  2. Multi-factor calibrated formula:
       final_score = (
           0.30 * evidence_strength
         + 0.25 * retrieval_relevance
         + 0.15 * query_coverage
         + 0.10 * temporal_accuracy
         + 0.10 * source_consistency
         + 0.10 * intent_certainty
       ) - penalties
  3. No blanket 95%:
     - Exact structured match: ~0.90 - 0.98 (HIGH)
     - Corroborated structured + semantic: ~0.95 - 0.99 (HIGH)
     - Strong semantic match only: ~0.75 - 0.85 (HIGH / upper MEDIUM)
     - Moderate semantic match: ~0.55 - 0.70 (MEDIUM)
     - Weak semantic match: ~0.35 - 0.50 (LOW)
     - Broad query / partial coverage: ~0.45 - 0.65 (MEDIUM)
     - No evidence: <= 0.25 (UNKNOWN)
  4. Clinical safety:
     Missing records never equal negative facts. Lack of evidence yields UNKNOWN.
"""

from datetime import date
import re
from typing import Any

from app.ai.memory_engine.intent_detector import PMEIntent
from app.ai.memory_engine.temporal_parser import parse_temporal_context, TemporalContext
from app.core.config import get_settings
from app.domains.voice.schemas import GroundedSource
from app.domains.memories.models import MemoryType
from app.domains.timeline.models import EventType

settings = get_settings()


class ConfidenceResult(tuple):
    """
    Tuple of (score, level, sources) providing backward-compatibility for 3-item unpacking:
      score, level, sources = ConfidenceEngine.evaluate(...)
    while exposing factors, score, level, sources via attributes:
      result.factors -> dict[str, float]
    """
    factors: dict[str, float]

    def __new__(
        cls,
        score: float,
        level: str,
        sources: list[GroundedSource],
        factors: dict[str, float] | None = None,
    ):
        instance = super().__new__(cls, (score, level, sources))
        instance.factors = factors or {}
        return instance

    @property
    def score(self) -> float:
        return self[0]

    @property
    def level(self) -> str:
        return self[1]

    @property
    def sources(self) -> list[GroundedSource]:
        return self[2]


class ConfidenceEngine:
    @staticmethod
    def evaluate(
        intent: PMEIntent,
        retrieved_data: dict[str, Any],
        query: str | None = None,
        entities: dict[str, Any] | None = None,
        reference_date: date | None = None,
    ) -> ConfidenceResult:
        """
        Calculates deterministic, multi-factor confidence score (0.0 - 1.0) based on
        claim-level grounding, entity matching, subject direction, and intent-aware weights.
        """
        sources: list[GroundedSource] = []
        seen_source_ids: set[str] = set()

        def _add_source(source: GroundedSource) -> None:
            if source.id not in seen_source_ids:
                seen_source_ids.add(source.id)
                sources.append(source)

        q = (query or "").lower().strip()
        entities = entities or {}

        # ── 1. Parse Temporal Context ─────────────────────────────────────────
        temporal: TemporalContext | None = entities.get("temporal")
        if temporal is None and query:
            temporal = parse_temporal_context(query, reference_date=reference_date)

        # ── 2. Extract Semantic Matches & Unified Memories ────────────────────
        unified_memories = retrieved_data.get("unified_memories", [])
        top_semantic_sim = 0.0
        if unified_memories:
            top_semantic_sim = max((m.get("similarity", 0.0) for m in unified_memories), default=0.0)

        # Base factor placeholders
        evidence_strength = 0.10
        retrieval_relevance = 0.10
        query_coverage = 0.10
        temporal_accuracy = 0.90
        source_consistency = 0.20
        intent_certainty = 0.85
        entity_match = 1.0
        subject_match = 1.0
        predicate_match = 1.0
        is_claim_grounded = True
        has_structured_evidence = False

        # ── 3. Intent Certainty Calculation ───────────────────────────────────
        if query:
            broad_patterns = [
                "what happened", "what did i do", "how was my day", "tell me about my day",
                "anything happen", "what's going on", "what is going on", "how did i do",
            ]
            if any(bp in q for bp in broad_patterns):
                intent_certainty = 0.70
            elif intent == PMEIntent.UNKNOWN:
                intent_certainty = 0.25
            elif intent == PMEIntent.GENERAL_CONVERSATION:
                greeting_words = ["hello", "namaste", "hi", "good morning", "good evening", "good afternoon"]
                if any(q.startswith(gw) for gw in greeting_words):
                    intent_certainty = 0.95
                else:
                    intent_certainty = 0.70
            else:
                intent_certainty = 0.95
        else:
            if intent == PMEIntent.GENERAL_CONVERSATION:
                intent_certainty = 0.65
            elif intent == PMEIntent.UNKNOWN:
                intent_certainty = 0.25
            else:
                intent_certainty = 0.90

        # ── 4. Domain-Specific Claim Grounding & Evidence Evaluation ──────────

        # 4.1 PERSON LOOKUP (Atemporal identity lookup)
        if intent == PMEIntent.PERSON_LOOKUP:
            matched_person = retrieved_data.get("matched_person")
            exact_match = retrieved_data.get("exact_match", False)
            target_name = entities.get("target_name")

            if matched_person and exact_match:
                has_structured_evidence = True
                entity_match = 1.0
                subject_match = 1.0
                predicate_match = 1.0
                _add_source(
                    GroundedSource(
                        source_type="person",
                        id=str(matched_person.id),
                        title=matched_person.name,
                        summary=f"Relationship: {matched_person.relationship or 'Family/Friend'}",
                    )
                )
                evidence_strength = 0.96
                retrieval_relevance = 0.98
                query_coverage = 0.95
                source_consistency = 0.85
                temporal_accuracy = 0.0  # Atemporal query; factor weight is 0.0

                for um in unified_memories[:2]:
                    m = um["memory"]
                    _add_source(
                        GroundedSource(
                            source_type="memory",
                            id=str(m.id),
                            title=m.title,
                            summary=f"Date: {m.event_date.strftime('%b %d, %Y')} | {m.description or ''}"[:120],
                            date=m.event_date.strftime("%Y-%m-%d"),
                        )
                    )
                if unified_memories and top_semantic_sim >= 0.75:
                    source_consistency = 0.98
                    evidence_strength = 0.98

            elif unified_memories and top_semantic_sim >= 0.45:
                m = unified_memories[0]["memory"]
                _add_source(
                    GroundedSource(
                        source_type="memory",
                        id=str(m.id),
                        title=m.title,
                        summary=f"Semantic memory match ({int(top_semantic_sim * 100)}%)",
                        date=m.event_date.strftime("%Y-%m-%d"),
                    )
                )
                entity_match = 0.85
                subject_match = 1.0
                evidence_strength = min(0.85, top_semantic_sim)
                retrieval_relevance = top_semantic_sim
                query_coverage = 0.75
                source_consistency = 0.70
                temporal_accuracy = 0.0
            else:
                entity_match = 0.0 if target_name else 0.5
                is_claim_grounded = False
                evidence_strength = 0.10
                retrieval_relevance = 0.10
                query_coverage = 0.10
                source_consistency = 0.10
                temporal_accuracy = 0.0

        # 4.2 VISIT RECALL (Direction-Aware, Entity-Constrained)
        elif intent == PMEIntent.VISIT_RECALL:
            memories = retrieved_data.get("memories", [])
            events = retrieved_data.get("timeline_events", [])
            target_name = entities.get("target_name")
            direction = entities.get("direction")  # "outgoing" vs "incoming" vs "neutral"

            matching_memories = memories
            matching_events = events

            if target_name:
                t_lower = target_name.lower()
                matching_memories = [
                    m for m in memories
                    if any(t_lower in p.name.lower() for p in m.people)
                    or t_lower in m.title.lower()
                    or (m.description and t_lower in m.description.lower())
                    or (m.location and t_lower in m.location.lower())
                ]
                matching_events = [
                    ev for ev in events
                    if t_lower in ev.title.lower()
                    or (ev.description and t_lower in ev.description.lower())
                    or (ev.location and t_lower in ev.location.lower())
                ]
                entity_match = 1.0 if (matching_memories or matching_events) else 0.0
            else:
                entity_match = 1.0 if (memories or events) else 0.0

            # Direction & Subject Grounding Check:
            # "Did I visit London/Rahul?" (outgoing) requires an OUTING or matching location.
            # An incoming family visit ("Rahul visited patient") does NOT support "I visited London"!
            if direction == "outgoing":
                has_outgoing = False
                for m in matching_memories:
                    m_type = m.memory_type.value if hasattr(m.memory_type, "value") else str(m.memory_type)
                    if m_type == "OUTING" or (m.location and target_name and target_name.lower() in m.location.lower()):
                        has_outgoing = True
                        break
                for ev in matching_events:
                    ev_type = ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type)
                    if ev_type == "OUTING" or (ev.location and target_name and target_name.lower() in ev.location.lower()):
                        has_outgoing = True
                        break
                subject_match = 1.0 if has_outgoing else 0.0
            elif direction == "incoming":
                subject_match = 1.0 if (matching_memories or matching_events) else 0.0
            else:
                subject_match = 1.0 if (matching_memories or matching_events) else 0.0

            if target_name and (entity_match < 0.5 or subject_match < 0.5):
                is_claim_grounded = False

            # Gating: If claim is NOT grounded, DO NOT include unrelated visits in sources!
            if is_claim_grounded and (matching_memories or matching_events):
                has_structured_evidence = True
                for m in matching_memories:
                    people_str = ", ".join(p.name for p in m.people) if m.people else "Family"
                    _add_source(
                        GroundedSource(
                            source_type="memory",
                            id=str(m.id),
                            title=f"Visit: {m.title}",
                            summary=f"{people_str} visited on {m.event_date.strftime('%b %d, %Y')}",
                            date=m.event_date.strftime("%Y-%m-%d"),
                        )
                    )
                for ev in matching_events:
                    _add_source(
                        GroundedSource(
                            source_type="event",
                            id=str(ev.id),
                            title=ev.title,
                            summary=f"Event at {ev.start_time.strftime('%I:%M %p, %b %d')}",
                            date=ev.start_time.strftime("%Y-%m-%d"),
                        )
                    )
                evidence_strength = 0.95
                retrieval_relevance = 0.95
                query_coverage = 0.90
                source_consistency = 0.85 if len(sources) == 1 else 0.92
                temporal_accuracy = 1.0 if (temporal and temporal.is_bounded) else 0.90

                if top_semantic_sim >= 0.75:
                    source_consistency = 0.98
                    evidence_strength = 0.98
            elif is_claim_grounded and unified_memories and top_semantic_sim >= 0.45:
                m = unified_memories[0]["memory"]
                _add_source(
                    GroundedSource(
                        source_type="memory",
                        id=str(m.id),
                        title=m.title,
                        summary=f"Semantic memory match ({int(top_semantic_sim * 100)}%)",
                        date=m.event_date.strftime("%Y-%m-%d"),
                    )
                )
                evidence_strength = min(0.80, top_semantic_sim)
                retrieval_relevance = top_semantic_sim
                query_coverage = 0.70
                source_consistency = 0.65
                temporal_accuracy = 0.80
            else:
                # Claim ungrounded or no evidence
                evidence_strength = 0.10
                retrieval_relevance = 0.05
                query_coverage = 0.10
                source_consistency = 0.10
                temporal_accuracy = 0.30 if (temporal and temporal.is_bounded) else 0.70

        # 4.3 MEDICATION ADHERENCE (Medication-Gated)
        elif intent == PMEIntent.MEDICATION_ADHERENCE:
            items = retrieved_data.get("items", [])
            has_meds = retrieved_data.get("has_medications", False)
            target_med = entities.get("target_medication")

            matching_items = items
            if target_med:
                t_lower = target_med.lower()
                matching_items = [it for it in items if t_lower in it["medication"].name.lower()]
                entity_match = 1.0 if matching_items else 0.0
            else:
                entity_match = 1.0 if (has_meds and items) else 0.0

            subject_match = 1.0

            if target_med and entity_match < 0.5:
                is_claim_grounded = False

            if is_claim_grounded and matching_items:
                has_structured_evidence = True
                has_direct_log = False
                for it in matching_items:
                    m = it["medication"]
                    status_str = "Taken" if it["is_taken"] else "Pending / Missed"
                    time_str = f" at {it['taken_at'].strftime('%I:%M %p')}" if it["taken_at"] else ""
                    if it["taken_at"] is not None or it.get("log") is not None:
                        has_direct_log = True
                    _add_source(
                        GroundedSource(
                            source_type="medication",
                            id=str(m.id),
                            title=f"{m.name} ({m.dosage or ''})",
                            summary=f"Status: {status_str}{time_str}",
                        )
                    )
                if has_direct_log:
                    evidence_strength = 0.98
                    retrieval_relevance = 0.98
                    query_coverage = 0.98
                    source_consistency = 0.92
                    temporal_accuracy = 1.0
                else:
                    evidence_strength = 0.82
                    retrieval_relevance = 0.88
                    query_coverage = 0.80
                    source_consistency = 0.75
                    temporal_accuracy = 0.90
            else:
                # No matching medication found
                evidence_strength = 0.10
                retrieval_relevance = 0.05
                query_coverage = 0.10
                source_consistency = 0.10
                temporal_accuracy = 0.30

        # 4.4 MEDICATION SCHEDULE
        elif intent == PMEIntent.MEDICATION_SCHEDULE:
            medications = retrieved_data.get("medications", [])
            has_meds = retrieved_data.get("has_medications", False)

            for m in medications:
                timing_label = m.timing.value if hasattr(m.timing, "value") else str(m.timing)
                _add_source(
                    GroundedSource(
                        source_type="medication",
                        id=str(m.id),
                        title=f"{m.name} ({m.dosage or 'standard dose'})",
                        summary=f"Scheduled: {timing_label}",
                        details=f"Frequency: {m.frequency.value if hasattr(m.frequency, "value") else m.frequency}",
                    )
                )

            if has_meds and medications:
                has_structured_evidence = True
                entity_match = 1.0
                subject_match = 1.0
                evidence_strength = 0.95
                retrieval_relevance = 0.95
                query_coverage = 0.92
                source_consistency = 0.88
                temporal_accuracy = 1.0 if (temporal and temporal.timing) else 0.95
            else:
                entity_match = 0.0
                is_claim_grounded = False
                evidence_strength = 0.10
                retrieval_relevance = 0.10
                query_coverage = 0.10
                source_consistency = 0.10

        # 4.5 GAME PROGRESS (Game-Constrained)
        elif intent == PMEIntent.GAME_PROGRESS:
            sessions = retrieved_data.get("sessions", [])
            has_sessions = retrieved_data.get("has_sessions", False)
            specific_game_queried = entities.get("game_name")

            matching_sessions = sessions
            if specific_game_queried:
                g_lower = specific_game_queried.lower()
                matching_sessions = [
                    s for s in sessions
                    if s.game and g_lower in s.game.name.lower()
                ]
                entity_match = 1.0 if matching_sessions else 0.0
            else:
                entity_match = 1.0 if (has_sessions and sessions) else 0.0

            subject_match = 1.0

            if specific_game_queried and entity_match < 0.5:
                is_claim_grounded = False

            if is_claim_grounded and matching_sessions:
                has_structured_evidence = True
                for s in matching_sessions:
                    game_title = s.game.name if (s.game and hasattr(s.game, "name")) else "Cognitive Game"
                    acc_pct = f"{int(s.accuracy * 100)}%" if s.accuracy is not None else "N/A"
                    rt_str = f"{s.reaction_time_ms}ms" if s.reaction_time_ms is not None else "N/A"
                    date_str = s.started_at.strftime("%Y-%m-%d") if s.started_at else None

                    _add_source(
                        GroundedSource(
                            source_type="game_session",
                            id=str(s.id),
                            title=game_title,
                            summary=f"Accuracy: {acc_pct} | Reaction: {rt_str} | Score: {s.score or 0}",
                            date=date_str,
                            details=f"Mistakes: {s.mistakes or 0}",
                        )
                    )
                evidence_strength = 0.95
                retrieval_relevance = 0.98 if specific_game_queried else 0.95
                query_coverage = 0.95 if specific_game_queried else (0.92 if len(sessions) >= 2 else 0.82)
                source_consistency = 0.88 if len(matching_sessions) >= 2 else 0.80
                temporal_accuracy = 1.0 if (temporal and temporal.is_bounded) else 0.90
            else:
                evidence_strength = 0.10
                retrieval_relevance = 0.05
                query_coverage = 0.10
                source_consistency = 0.10
                temporal_accuracy = 0.25 if (temporal and temporal.is_bounded) else 0.80

        # 4.6 COGNITIVE PROGRESS & CPI TREND
        elif intent == PMEIntent.COGNITIVE_PROGRESS:
            metrics = retrieved_data.get("cognitive_metrics", [])
            daily_stats = retrieved_data.get("daily_stats", [])
            has_data = retrieved_data.get("has_data", False)

            if metrics:
                latest_m = metrics[0]
                cpi_val = f"{int(latest_m.cpi_score)}" if latest_m.cpi_score is not None else "N/A"
                delta_val = f"{latest_m.cpi_delta:+.1f}" if latest_m.cpi_delta is not None else "0.0"
                trend_val = retrieved_data.get("cpi_trend", "stable")
                date_str = latest_m.metric_date.strftime("%Y-%m-%d") if latest_m.metric_date else None

                _add_source(
                    GroundedSource(
                        source_type="cognitive_metric",
                        id=str(latest_m.id),
                        title=f"CPI Index: {cpi_val}",
                        summary=f"Trend: {trend_val} (Delta: {delta_val})",
                        date=date_str,
                        details=f"Memory: {int((latest_m.memory_accuracy or 0)*100)}% | Reaction: {int((latest_m.reaction_performance or 0)*100)}%",
                    )
                )

            for ds in daily_stats[:2]:
                date_str = ds.stat_date.strftime("%Y-%m-%d") if ds.stat_date else None
                _add_source(
                    GroundedSource(
                        source_type="daily_statistic",
                        id=str(ds.id),
                        title=f"Daily Activity ({date_str})",
                        summary=f"Games: {ds.games_completed}/{ds.games_total} | Meds: {ds.medications_taken}/{ds.medications_scheduled}",
                        date=date_str,
                    )
                )

            if has_data and (metrics or daily_stats):
                has_structured_evidence = True
                entity_match = 1.0
                subject_match = 1.0
                evidence_strength = 0.94
                retrieval_relevance = 0.94
                query_coverage = 0.90
                source_consistency = 0.90 if (metrics and daily_stats) else 0.82
                temporal_accuracy = 0.95
            else:
                entity_match = 0.0
                is_claim_grounded = False
                evidence_strength = 0.10
                retrieval_relevance = 0.10
                query_coverage = 0.10
                source_consistency = 0.10
                temporal_accuracy = 0.40

        # 4.7 EVENT / CALENDAR LOOKUP
        elif intent == PMEIntent.EVENT_LOOKUP:
            events = retrieved_data.get("events", [])
            has_events = retrieved_data.get("has_events", False)

            for ev in events:
                time_str = ev.start_time.strftime("%b %d, %I:%M %p")
                loc_str = f" at {ev.location}" if ev.location else ""
                date_str = ev.start_time.strftime("%Y-%m-%d")
                _add_source(
                    GroundedSource(
                        source_type="event",
                        id=str(ev.id),
                        title=ev.title,
                        summary=f"Time: {time_str}{loc_str}",
                        date=date_str,
                        details=ev.description or None,
                    )
                )

            if has_events and events:
                has_structured_evidence = True
                entity_match = 1.0
                subject_match = 1.0
                evidence_strength = 0.95
                retrieval_relevance = 0.95
                query_coverage = 0.92
                source_consistency = 0.85
                temporal_accuracy = 1.0 if (temporal and temporal.is_bounded) else 0.90
            else:
                entity_match = 0.0
                is_claim_grounded = False
                evidence_strength = 0.10
                retrieval_relevance = 0.10
                query_coverage = 0.10
                source_consistency = 0.10
                temporal_accuracy = 0.25 if (temporal and temporal.is_bounded) else 0.80

        # 4.8 DAILY ROUTINE
        elif intent == PMEIntent.DAILY_ROUTINE:
            routines = retrieved_data.get("routines", [])
            events = retrieved_data.get("events", [])

            for r in routines[:4]:
                _add_source(
                    GroundedSource(
                        source_type="routine",
                        id=str(r.id),
                        title=r.title,
                        summary=f"Time: {r.scheduled_time.strftime('%I:%M %p')} | Category: {r.category.value if hasattr(r.category, 'value') else r.category}",
                    )
                )

            for ev in events[:2]:
                _add_source(
                    GroundedSource(
                        source_type="event",
                        id=str(ev.id),
                        title=ev.title,
                        summary=f"Event at {ev.start_time.strftime('%I:%M %p')}",
                        date=ev.start_time.strftime("%Y-%m-%d"),
                    )
                )

            if routines or events:
                has_structured_evidence = True
                entity_match = 1.0
                subject_match = 1.0
                evidence_strength = 0.92
                retrieval_relevance = 0.92
                query_coverage = 0.88
                source_consistency = 0.85 if (routines and events) else 0.80
                temporal_accuracy = 0.95
            else:
                entity_match = 0.0
                is_claim_grounded = False
                evidence_strength = 0.10
                retrieval_relevance = 0.10
                query_coverage = 0.10
                source_consistency = 0.10
                temporal_accuracy = 0.30

        # 4.9 BROAD TEMPORAL RECALL (What happened yesterday?)
        elif intent == PMEIntent.TEMPORAL_RECALL:
            memories = retrieved_data.get("memories", [])
            events = retrieved_data.get("events", [])
            sessions = retrieved_data.get("game_sessions", [])
            med_logs = retrieved_data.get("medication_logs", [])
            has_data = retrieved_data.get("has_data", False)

            if has_data:
                has_structured_evidence = True
                entity_match = 1.0
                subject_match = 1.0
                predicate_match = 1.0
                temporal_accuracy = 1.0

                for m in memories[:2]:
                    _add_source(GroundedSource(
                        source_type="memory",
                        id=str(m.id),
                        title=f"Visit: {m.title}",
                        summary=f"Date: {m.event_date.strftime('%Y-%m-%d')}",
                        date=m.event_date.strftime("%Y-%m-%d"),
                    ))
                for ev in events[:2]:
                    _add_source(GroundedSource(
                        source_type="event",
                        id=str(ev.id),
                        title=ev.title,
                        summary=f"Time: {ev.start_time.strftime('%I:%M %p')}",
                        date=ev.start_time.strftime("%Y-%m-%d"),
                    ))
                for s in sessions[:2]:
                    g_name = s.game.name if (s.game and hasattr(s.game, "name")) else "Cognitive Game"
                    _add_source(GroundedSource(
                        source_type="game_session",
                        id=str(s.id),
                        title=g_name,
                        summary=f"Score: {s.score or 0}",
                        date=s.started_at.strftime("%Y-%m-%d") if s.started_at else None,
                    ))
                for log in med_logs[:2]:
                    med_name = log.medication.name if (log.medication and hasattr(log.medication, "name")) else "Medication"
                    _add_source(GroundedSource(
                        source_type="medication",
                        id=str(log.id),
                        title=med_name,
                        summary=f"Taken: {'Yes' if log.taken else 'No'}",
                        date=log.log_date.strftime("%Y-%m-%d"),
                    ))

                evidence_strength = 0.92
                retrieval_relevance = 0.92
                query_coverage = 0.90 if (memories and (sessions or med_logs)) else 0.75
                source_consistency = 0.88
            else:
                entity_match = 0.0
                is_claim_grounded = False
                evidence_strength = 0.10
                retrieval_relevance = 0.10
                query_coverage = 0.10
                temporal_accuracy = 0.25
                source_consistency = 0.10

        # 4.10 GENERAL CONVERSATION / SEMANTIC RETRIEVAL
        else:
            if unified_memories and top_semantic_sim >= 0.45:
                for um in unified_memories[:2]:
                    if um.get("similarity", 0.0) >= 0.45:
                        m = um["memory"]
                        _add_source(
                            GroundedSource(
                                source_type="memory",
                                id=str(m.id),
                                title=m.title,
                                summary=f"Semantic Match ({int(um['similarity'] * 100)}%)",
                                date=m.event_date.strftime("%Y-%m-%d"),
                            )
                        )

                if top_semantic_sim >= 0.85:
                    evidence_strength = 0.92
                    retrieval_relevance = top_semantic_sim
                    query_coverage = 0.88
                    source_consistency = 0.85
                    temporal_accuracy = 0.90
                    intent_certainty = 0.90
                elif top_semantic_sim >= 0.75:
                    evidence_strength = top_semantic_sim
                    retrieval_relevance = top_semantic_sim
                    query_coverage = 0.76
                    source_consistency = 0.70
                    temporal_accuracy = 0.90
                elif top_semantic_sim >= 0.60:
                    evidence_strength = top_semantic_sim * 0.85
                    retrieval_relevance = top_semantic_sim
                    query_coverage = 0.58
                    source_consistency = 0.50
                    temporal_accuracy = 0.75
                else:
                    evidence_strength = 0.38
                    retrieval_relevance = top_semantic_sim
                    query_coverage = 0.42
                    source_consistency = 0.35
                    temporal_accuracy = 0.65
            elif intent == PMEIntent.GENERAL_CONVERSATION:
                greeting_words = ["hello", "namaste", "hi", "good morning", "good evening", "good afternoon"]
                if any(q.startswith(gw) for gw in greeting_words):
                    evidence_strength = 0.90
                    retrieval_relevance = 0.90
                    query_coverage = 0.90
                    source_consistency = 0.85
                    temporal_accuracy = 1.0
                else:
                    evidence_strength = 0.30
                    retrieval_relevance = 0.30
                    query_coverage = 0.30
                    source_consistency = 0.20
                    temporal_accuracy = 0.50
            else:
                is_claim_grounded = False
                evidence_strength = 0.10
                retrieval_relevance = 0.10
                query_coverage = 0.10
                source_consistency = 0.10
                temporal_accuracy = 0.25

        # ── 5. Query Coverage & Grounding Penalties ───────────────────────────
        penalties = 0.0

        if not is_claim_grounded:
            penalties += 0.35

        # Broad query with sparse coverage
        if query and any(bp in q for bp in ["what happened", "what did i do", "tell me about my day", "anything happen"]):
            if len(sources) == 1 and not has_structured_evidence:
                query_coverage = min(query_coverage, 0.50)
                penalties += 0.10
            elif len(sources) <= 1 and has_structured_evidence and intent not in [
                PMEIntent.MEDICATION_ADHERENCE, PMEIntent.PERSON_LOOKUP, PMEIntent.VISIT_RECALL, PMEIntent.TEMPORAL_RECALL
            ]:
                query_coverage = min(query_coverage, 0.60)
                penalties += 0.08

        # Unmatched query tokens penalty
        if query and sources:
            stop_words = {
                "did", "i", "you", "my", "me", "what", "how", "who", "when", "where",
                "was", "were", "is", "are", "the", "a", "an", "this", "that", "today",
                "yesterday", "tomorrow", "morning", "afternoon", "evening", "night",
                "to", "in", "at", "on", "for", "with", "about", "visit", "visited",
                "have", "had", "do", "any", "some", "our", "there", "here", "come", "came",
                "appointment", "appointments", "event", "events", "calendar", "routine", "routines",
                "schedule", "scheduled", "plan", "plans", "medicine", "medication", "medications",
                "pill", "pills", "game", "games", "tell", "show"
            }
            query_tokens = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", q) if w not in stop_words]
            if query_tokens:
                combined_source_text = " ".join(
                    f"{s.title} {s.summary or ''} {s.details or ''}".lower() for s in sources
                )
                matching_tokens = [t for t in query_tokens if t in combined_source_text]
                if not matching_tokens and intent in [PMEIntent.VISIT_RECALL, PMEIntent.PERSON_LOOKUP, PMEIntent.EVENT_LOOKUP]:
                    retrieval_relevance = 0.15
                    evidence_strength = 0.15
                    query_coverage = 0.15
                    source_consistency = 0.15
                    penalties += 0.25

        if intent_certainty < 0.70:
            penalties += 0.08

        # ── 6. Intent-Aware Factor Weighted Score ─────────────────────────────
        intent_weights_map: dict[PMEIntent, dict[str, float]] = {
            PMEIntent.PERSON_LOOKUP: {
                "evidence_strength": 0.35,
                "entity_match": 0.25,
                "retrieval_relevance": 0.20,
                "query_coverage": 0.10,
                "source_consistency": 0.10,
                "temporal_accuracy": 0.00,  # Person profile is atemporal
            },
            PMEIntent.MEDICATION_ADHERENCE: {
                "evidence_strength": 0.25,
                "entity_match": 0.25,
                "temporal_accuracy": 0.20,
                "subject_match": 0.15,
                "retrieval_relevance": 0.10,
                "source_consistency": 0.05,
            },
            PMEIntent.GAME_PROGRESS: {
                "evidence_strength": 0.25,
                "entity_match": 0.25,
                "temporal_accuracy": 0.20,
                "retrieval_relevance": 0.15,
                "query_coverage": 0.10,
                "source_consistency": 0.05,
            },
            PMEIntent.VISIT_RECALL: {
                "entity_match": 0.25,
                "subject_match": 0.20,
                "evidence_strength": 0.20,
                "temporal_accuracy": 0.15,
                "retrieval_relevance": 0.10,
                "source_consistency": 0.10,
            },
            PMEIntent.TEMPORAL_RECALL: {
                "evidence_strength": 0.25,
                "temporal_accuracy": 0.25,
                "query_coverage": 0.20,
                "retrieval_relevance": 0.15,
                "source_consistency": 0.15,
            },
            PMEIntent.DAILY_ROUTINE: {
                "evidence_strength": 0.30,
                "retrieval_relevance": 0.25,
                "query_coverage": 0.20,
                "temporal_accuracy": 0.15,
                "source_consistency": 0.10,
            },
            PMEIntent.EVENT_LOOKUP: {
                "evidence_strength": 0.30,
                "retrieval_relevance": 0.25,
                "temporal_accuracy": 0.20,
                "query_coverage": 0.15,
                "source_consistency": 0.10,
            },
            PMEIntent.MEDICATION_SCHEDULE: {
                "evidence_strength": 0.30,
                "retrieval_relevance": 0.25,
                "query_coverage": 0.20,
                "temporal_accuracy": 0.15,
                "source_consistency": 0.10,
            },
        }

        weights = intent_weights_map.get(intent, {
            "evidence_strength": 0.30,
            "retrieval_relevance": 0.25,
            "query_coverage": 0.15,
            "temporal_accuracy": 0.10,
            "source_consistency": 0.10,
            "intent_certainty": 0.10,
        })

        all_factor_vals = {
            "evidence_strength": evidence_strength,
            "retrieval_relevance": retrieval_relevance,
            "query_coverage": query_coverage,
            "temporal_accuracy": temporal_accuracy,
            "source_consistency": source_consistency,
            "intent_certainty": intent_certainty,
            "entity_match": entity_match,
            "subject_match": subject_match,
            "predicate_match": predicate_match,
        }

        base_score = sum(weights.get(k, 0.0) * all_factor_vals.get(k, 0.0) for k in weights)
        final_score = base_score - penalties

        # Safeguard caps: Non-grounded claims or zero supporting sources must NEVER receive HIGH/MEDIUM
        if not is_claim_grounded or not sources:
            final_score = min(final_score, 0.20)
        elif not has_structured_evidence and top_semantic_sim < 0.55:
            final_score = min(final_score, 0.48)

        final_score = max(0.0, min(1.0, final_score))

        # ── 7. Confidence Level Determination ─────────────────────────────────
        high_thresh = getattr(settings, "CONFIDENCE_HIGH_THRESHOLD", 0.75)
        med_thresh = getattr(settings, "CONFIDENCE_MEDIUM_THRESHOLD", 0.50)
        low_thresh = getattr(settings, "CONFIDENCE_LOW_THRESHOLD", 0.30)

        if final_score >= high_thresh:
            level = "HIGH"
        elif final_score >= med_thresh:
            level = "MEDIUM"
        elif final_score >= low_thresh:
            level = "LOW"
        else:
            level = "UNKNOWN"

        factors = {
            "evidence_strength": round(evidence_strength, 3),
            "retrieval_relevance": round(retrieval_relevance, 3),
            "query_coverage": round(query_coverage, 3),
            "temporal_accuracy": round(temporal_accuracy, 3),
            "source_consistency": round(source_consistency, 3),
            "intent_certainty": round(intent_certainty, 3),
            "entity_match": round(entity_match, 3),
            "subject_match": round(subject_match, 3),
        }

        return ConfidenceResult(final_score, level, sources, factors)

