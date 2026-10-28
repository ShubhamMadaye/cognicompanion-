"""
CogniCompanion — PME Hybrid Ranker
===================================
Fuses structured database evidence and semantic memory retrieval into a
coherent, deduplicated, and prioritised evidence package.

Principles:
  - Factual queries (medication, visits, routines, person lookups) prioritize structured records.
  - Narrative queries ("Tell me about...", "What do you remember about...") weigh semantic memories strongly.
  - Deduplication: If a memory is retrieved both structurally and semantically, it is unified
    with an augmented evidence score and merged provenance.
"""

import uuid
from typing import Any

from app.ai.memory_engine.intent_detector import PMEIntent
from app.domains.memories.models import Memory, Person
from app.domains.timeline.models import Event, Medication, Routine


class HybridRanker:
    @staticmethod
    def rank_and_deduplicate(
        intent: PMEIntent,
        structured_data: dict[str, Any],
        semantic_matches: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Merges and deduplicates structured data and semantic matches.
        Returns a unified dictionary suitable for ContextBuilder and ConfidenceEngine.
        """
        combined = dict(structured_data)
        seen_memory_ids: set[uuid.UUID] = set()

        unified_memories: list[dict[str, Any]] = []

        # 1. Process structured memories (from visit retrieval or person-associated memories)
        raw_structured_memories: list[Memory] = []
        if "memories" in structured_data and structured_data["memories"]:
            raw_structured_memories.extend(structured_data["memories"])
        if "related_memories" in structured_data and structured_data["related_memories"]:
            raw_structured_memories.extend(structured_data["related_memories"])

        # Map semantic matches by memory.id for instant fusion
        semantic_by_id = {match["memory"].id: match for match in semantic_matches}

        for mem in raw_structured_memories:
            if mem.id in seen_memory_ids:
                continue
            seen_memory_ids.add(mem.id)

            sem_info = semantic_by_id.get(mem.id)
            sem_sim = sem_info["similarity"] if sem_info else 0.0
            composite = 0.95 if not sem_info else min(1.0, 0.95 + (sem_sim * 0.05))

            unified_memories.append({
                "memory": mem,
                "provenance": "structured_and_semantic" if sem_info else "structured",
                "similarity": sem_sim,
                "score": composite,
                "is_structured": True,
            })

        # 2. Add remaining semantic matches that were not retrieved structurally
        for match in semantic_matches:
            mem = match["memory"]
            if mem.id in seen_memory_ids:
                continue
            seen_memory_ids.add(mem.id)

            unified_memories.append({
                "memory": mem,
                "provenance": "semantic",
                "similarity": match["similarity"],
                "score": match["score"],
                "is_structured": False,
            })

        # 3. Sort unified memories based on query intent
        if intent in [PMEIntent.VISIT_RECALL, PMEIntent.MEDICATION_ADHERENCE, PMEIntent.DAILY_ROUTINE]:
            # Structured factual evidence strictly takes precedence
            unified_memories.sort(
                key=lambda x: (1 if x["is_structured"] else 0, x["score"]),
                reverse=True,
            )
        else:
            # Narrative & person queries: score-based hybrid ranking
            unified_memories.sort(key=lambda x: x["score"], reverse=True)

        combined["unified_memories"] = unified_memories
        combined["semantic_matches"] = semantic_matches

        # Deduplicate timeline events if any
        if "timeline_events" in combined and combined["timeline_events"]:
            seen_events = set()
            unique_events = []
            for ev in combined["timeline_events"]:
                if ev.id not in seen_events:
                    seen_events.add(ev.id)
                    unique_events.append(ev)
            combined["timeline_events"] = unique_events

        return combined
