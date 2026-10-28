"""
CogniCompanion — Query Understanding Layer (QU)
================================================
Sits between raw patient speech and the Personalized Memory Engine.

Handles the full spectrum of imperfect elderly patient queries:
  - Incomplete questions ("Where?", "When?", "And Rahul?")
  - Pronoun references ("he", "she", "we", "they", "it")
  - Coreference resolution ("What about yesterday?" → medication intent + yesterday date)
  - Spelling errors ("Rhaul" → "Rahul", "medcine" → "medicine")
  - Malformed word-order ("rahul last sunday where")
  - Multi-memory compound questions ("When did I meet Rahul and what did we do?")
  - Ambiguity detection — NEVER guesses when multiple interpretations are equally plausible

Three operating modes:
  Mode A — Deterministic  (<5ms, no API call): pronoun resolution, bare follow-ups,
                           temporal inheritance when context is clear.
  Mode B — Gemini-Assisted (~200–600ms, 1 LLM call): malformed queries, compound
                           questions, structural ambiguity requiring semantic inference.
  Mode C — Clarification  (returns question in patient's language): when ambiguity
                           genuinely cannot be resolved without more information.

IMPORTANT — Never exposes QueryUnderstanding to the patient.
The patient receives only a natural spoken response.
QueryUnderstanding is internal and optionally shown in the caregiver explainability panel.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.ai.memory_engine.intent_detector import PMEIntent
from app.ai.memory_engine.temporal_parser import TemporalContext, parse_temporal_context

logger = logging.getLogger(__name__)


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class ConversationContext:
    """
    Short-term in-turn context rebuilt from the last 4 conversation_messages rows.
    Strictly scoped to a single patient. Never shared. Never persisted as long-term memory.
    """
    conversation_id: uuid.UUID | None
    patient_id: uuid.UUID
    language: str = "en"
    recent_turns: list[dict[str, Any]] = field(default_factory=list)
    last_intent: PMEIntent | None = None
    last_referenced_person: str | None = None
    last_referenced_event: str | None = None
    last_referenced_location: str | None = None
    last_referenced_date: date | None = None
    last_pme_evidence: list[str] = field(default_factory=list)
    # Known patient entities for spelling correction
    known_people: list[str] = field(default_factory=list)
    known_medications: list[str] = field(default_factory=list)


@dataclass
class QueryUnderstanding:
    """
    Internal structured output of the Query Understanding Layer.
    Never shown to the patient directly.
    Optionally surfaced to the caregiver explainability panel.
    """
    original_query: str
    language: str
    intent_hint: PMEIntent | None
    entities: dict[str, Any]
    date_reference: TemporalContext | None
    resolved_references: dict[str, str]   # e.g. {"he": "Rahul", "we": "patient+Rahul"}
    rewritten_query: str                  # Clean English query for PME retrieval
    needs_clarification: bool
    clarification_question: str | None    # In patient's language when needed
    resolution_mode: str                  # "deterministic" | "llm_assisted" | "clarification"
    confidence: float
    evidence_plan: list[str]              # For multi-memory queries


# ── Pronoun Tables ────────────────────────────────────────────────────────────

# English pronouns → role mapping
_PERSON_PRONOUNS = {"he", "she", "him", "her", "they", "them"}
_GROUP_PRONOUNS = {"we", "us", "our"}
_OBJECT_PRONOUNS = {"it", "that", "this"}

# Bare follow-up words/phrases that mean "repeat with same context"
_BARE_TEMPORAL = {
    "yesterday", "today", "last week", "this week", "last sunday", "last monday",
    "last tuesday", "last wednesday", "last thursday", "last friday", "last saturday",
}

# Single-word question words
_BARE_QUESTION_WORDS = {
    "where", "when", "who", "what", "how",
    # Assamese
    "ক'ত", "কেতিয়া", "কোন", "কি",
    # Hindi
    "कहाँ", "कब", "कौन", "क्या",
    # Mizo
    "kawnah", "kum thleng", "tu",
    # Khasi
    "ha", "nongkynmaw",
}

# Generic medical domain spelling corrections (supplements patient roster)
_MEDICAL_CORRECTIONS: dict[str, str] = {
    "medcine": "medicine", "medcin": "medicine", "medicne": "medicine",
    "medicien": "medicine", "medecine": "medicine",
    "tablt": "tablet", "tabllet": "tablet", "tabelt": "tablet",
    "pil": "pill", "pils": "pills",
    "doctr": "doctor", "doctir": "doctor", "dokter": "doctor",
    "hosptal": "hospital", "hospitl": "hospital",
    "daughtr": "daughter", "dautr": "daughter",
    "famly": "family", "familly": "family",
    "sundayy": "sunday", "sundai": "sunday",
    "medcation": "medication", "medicaton": "medication",
    "appointmnt": "appointment", "appoinment": "appointment",
}


# ── Levenshtein Edit Distance ─────────────────────────────────────────────────

def _levenshtein(s1: str, s2: str) -> int:
    """Compute Damerau-Levenshtein edit distance (includes adjacent transposition)."""
    s1, s2 = s1.lower(), s2.lower()
    if s1 == s2:
        return 0
    d: dict[tuple[int, int], int] = {}
    len1, len2 = len(s1), len(s2)
    for i in range(-1, len1 + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, len2 + 1):
        d[(-1, j)] = j + 1

    for i in range(len1):
        for j in range(len2):
            cost = 0 if s1[i] == s2[j] else 1
            d[(i, j)] = min(
                d[(i - 1, j)] + 1,       # deletion
                d[(i, j - 1)] + 1,       # insertion
                d[(i - 1, j - 1)] + cost # substitution
            )
            if i > 0 and j > 0 and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + 1) # transposition

    return d[(len1 - 1, len2 - 1)]


def _correct_spelling(query: str, context: ConversationContext | None) -> tuple[str, dict[str, str]]:
    """
    Corrects spelling errors in the query.
    Priority:
      1. Patient's own people names and medication names (via edit distance ≤ 1)
      2. Medical domain word list (exact match)
    Never corrects words that are already valid entity names.
    Returns (corrected_query, corrections_made_dict).
    """
    corrections: dict[str, str] = {}
    words = query.split()
    corrected_words: list[str] = []

    known_entities: list[str] = []
    if context:
        known_entities = context.known_people + context.known_medications

    for word in words:
        clean_word = re.sub(r"[^\w]", "", word.lower())

        # Skip very short words, stop words, and words already in entity list
        if len(clean_word) <= 2:
            corrected_words.append(word)
            continue
        # 0. Check if word matches a known entity case-insensitively -> canonicalize casing
        canonical_match = next((e for e in known_entities if clean_word == e.lower()), None)
        if canonical_match:
            _pm = re.match(r"^\W*", word)
            _sm = re.search(r"\W*$", word)
            prefix = _pm.group() if _pm else ""
            suffix = _sm.group() if _sm else ""
            canonical_word = prefix + canonical_match + suffix
            corrected_words.append(canonical_word)
            if word != canonical_word:
                corrections[word] = canonical_match
            continue

        # 1. Try entity roster match (edit distance <= 1 only for names, <= 2 for meds)
        best_entity_match: str | None = None
        best_dist = 999
        for entity in known_entities:
            dist = _levenshtein(clean_word, entity.lower())
            max_dist = 1 if entity in (context.known_people if context else []) else 2
            if dist <= max_dist and dist < best_dist:
                best_dist = dist
                best_entity_match = entity

        if best_entity_match and best_dist > 0:
            corrections[word] = best_entity_match
            # Preserve leading/trailing punctuation
            _pm2 = re.match(r"^\W*", word)
            _sm2 = re.search(r"\W*$", word)
            prefix = _pm2.group() if _pm2 else ""
            suffix = _sm2.group() if _sm2 else ""
            corrected_words.append(prefix + best_entity_match + suffix)
            continue

        # 2. Medical domain corrections (exact key match)
        if clean_word in _MEDICAL_CORRECTIONS:
            corrected = _MEDICAL_CORRECTIONS[clean_word]
            corrections[word] = corrected
            corrected_words.append(corrected)
            continue

        corrected_words.append(word)

    return " ".join(corrected_words), corrections


def _extract_pronouns(query: str) -> dict[str, str]:
    """Finds personal pronouns in the query and maps them to their type."""
    q_lower = query.lower()
    found: dict[str, str] = {}
    for p in _PERSON_PRONOUNS:
        if re.search(rf"\b{p}\b", q_lower):
            found[p] = "person"
    for p in _GROUP_PRONOUNS:
        if re.search(rf"\b{p}\b", q_lower):
            found[p] = "group"
    for p in _OBJECT_PRONOUNS:
        if re.search(rf"\b{p}\b", q_lower):
            found[p] = "object"
    return found


def _resolve_pronouns(
    query: str,
    pronouns_found: dict[str, str],
    context: ConversationContext | None,
) -> tuple[str, dict[str, str], bool]:
    """
    Attempts to resolve pronouns to named entities using context.
    Returns (rewritten_query, resolved_references, needs_clarification).
    """
    if not context or not pronouns_found:
        if pronouns_found and not context:
            # No context to resolve from — clarification needed only if the
            # entire meaningful content of the query is just the pronoun
            words = [w for w in query.lower().split() if re.sub(r"\W", "", w) not in
                     _PERSON_PRONOUNS | _GROUP_PRONOUNS | _OBJECT_PRONOUNS | {"?", ""}]
            if not words:
                return query, {}, True
        return query, {}, False

    resolved: dict[str, str] = {}
    rewritten = query
    needs_clarification = False

    for pronoun, ptype in pronouns_found.items():
        if ptype == "person":
            if context.last_referenced_person:
                resolved[pronoun] = context.last_referenced_person
                rewritten = re.sub(
                    rf"\b{pronoun}\b",
                    context.last_referenced_person,
                    rewritten,
                    flags=re.IGNORECASE,
                )
            else:
                needs_clarification = True

        elif ptype == "group":
            target_person = context.last_referenced_person
            if not target_person and context.known_people:
                for p in context.known_people:
                    if re.search(rf"\b{p}\b", query, flags=re.IGNORECASE):
                        target_person = p
                        break
            if target_person:
                group_label = f"the patient and {target_person}"
                resolved[pronoun] = group_label
                rewritten = re.sub(
                    rf"\b{pronoun}\b",
                    group_label,
                    rewritten,
                    flags=re.IGNORECASE,
                )
            else:
                needs_clarification = True

        elif ptype == "object":
            if context.last_referenced_event:
                resolved[pronoun] = context.last_referenced_event
                rewritten = re.sub(
                    rf"\b{pronoun}\b",
                    context.last_referenced_event,
                    rewritten,
                    flags=re.IGNORECASE,
                )

    return rewritten, resolved, needs_clarification


def _is_bare_followup(query: str) -> bool:
    """Returns True if the query is a bare follow-up (a single question word or very short)."""
    clean = query.strip().lower().rstrip("?").strip()
    # Single word
    if clean in _BARE_QUESTION_WORDS:
        return True
    # Very short fragment like "and rahul?" or "my daughter?"
    if len(clean.split()) <= 3 and not any(
        k in clean for k in ["medicine", "visit", "doctor", "game", "schedule", "routine"]
    ):
        return True
    return False


def _resolve_bare_followup(
    query: str,
    context: ConversationContext | None,
    reference_date: date | None,
) -> tuple[str, bool, str | None]:
    """
    Attempts to expand a bare follow-up query into a full question using context.
    Returns (rewritten_query, needs_clarification, clarification_question).
    """
    clean = query.strip().lower().rstrip("?").strip()

    if not context:
        return query, True, "Could you tell me a bit more about what you'd like to know?"

    # "When?" or "What time?" — expand using last person + last intent
    if clean in {"when", "kab", "केतिया"}:
        if context.last_referenced_person and context.last_intent == PMEIntent.VISIT_RECALL:
            return (
                f"When did {context.last_referenced_person} visit the patient?",
                False, None,
            )
        if context.last_intent == PMEIntent.MEDICATION_ADHERENCE:
            return "When did the patient take their medication?", False, None
        # Ambiguous
        return query, True, _build_clarification("when", context)

    # "Where?" — expand using last person + last visit context
    if clean in {"where", "kawnah", "ha", "कहाँ", "ক'ত"}:
        if context.last_referenced_person and context.last_intent == PMEIntent.VISIT_RECALL:
            return (
                f"Where did {context.last_referenced_person} visit the patient?",
                False, None,
            )
        if context.last_referenced_location:
            return f"Where is {context.last_referenced_location}?", False, None
        return query, True, _build_clarification("where", context)

    # "Who?" — expand using last event
    if clean in {"who", "tu", "कोन", "কোন"}:
        if context.last_referenced_event:
            return (
                f"Who was with the patient during {context.last_referenced_event}?",
                False, None,
            )
        return query, True, "Who are you asking about?"

    # "What?" or "What happened?" — expand using last person or event
    if clean in {"what", "what happened"}:
        if context.last_referenced_person and context.last_intent == PMEIntent.VISIT_RECALL:
            return (
                f"What did the patient and {context.last_referenced_person} do together?",
                False, None,
            )
        if context.last_referenced_event:
            return f"What happened during {context.last_referenced_event}?", False, None
        return query, True, "What would you like to know about?"

    # "And [Person]?" — continue same intent for a different person
    and_match = re.match(r"^(?:and\s+|what about\s+)(.+?)[\?]?$", clean)
    if and_match:
        subject = and_match.group(1).strip()
        if context and context.known_people:
            for p in context.known_people:
                if p.lower() == subject.lower():
                    subject = p
                    break
        else:
            subject = subject.title()
        if context.last_intent == PMEIntent.VISIT_RECALL:
            return f"When did {subject} visit the patient?", False, None
        if context.last_intent == PMEIntent.MEDICATION_ADHERENCE:
            return f"Did {subject} bring any medication to the patient?", False, None
        if context.last_intent == PMEIntent.PERSON_LOOKUP:
            return f"Tell me about {subject}.", False, None

    # "What about yesterday?" or "Yesterday?" — inherit intent with new date
    yesterday_match = re.search(r"\b(yesterday|last week|today)\b", clean)
    if yesterday_match:
        temporal = parse_temporal_context(query, reference_date=reference_date)
        if context.last_intent == PMEIntent.MEDICATION_ADHERENCE:
            return (
                f"Did the patient take their medication {yesterday_match.group(1)}?",
                False, None,
            )
        if context.last_intent == PMEIntent.VISIT_RECALL:
            person = context.last_referenced_person or "anyone"
            return (
                f"Did {person} visit the patient {yesterday_match.group(1)}?",
                False, None,
            )
        if context.last_intent == PMEIntent.DAILY_ROUTINE:
            return f"What was the patient's routine {yesterday_match.group(1)}?", False, None

    return query, False, None


def _build_clarification(question_word: str, context: ConversationContext) -> str:
    """Builds a natural clarification question when ambiguity exists."""
    recent_people = [
        t.get("person") for t in context.recent_turns
        if t.get("person") and t.get("role") == "assistant"
    ]
    unique_people = list(dict.fromkeys(p for p in recent_people if p))

    if len(unique_people) >= 2:
        return (
            f"Are you asking about {question_word} "
            f"{unique_people[0]} was here, or {question_word} {unique_people[1]} was here?"
        )
    if context.last_referenced_event:
        return f"Are you asking {question_word} {context.last_referenced_event} happened?"
    return f"Could you be more specific about {question_word} you are asking?"


# ── LLM-Assisted Rewriting ────────────────────────────────────────────────────

_QU_SYSTEM_PROMPT = """You are the Query Understanding module for CogniCompanion, an AI assistant for elderly dementia patients.

Your job is to analyze a potentially malformed, incomplete, or ambiguous patient query and return a JSON object.

RULES:
1. Preserve the patient's EXACT intent. Do not change what they are asking.
2. Preserve all named entities (people's names, medication names, dates).
3. Correct obvious spelling errors using the provided known entities.
4. Resolve pronouns (he/she/they/we/it) using the conversation context.
5. If the query is a bare follow-up (e.g. "Where?", "When?", "And Rahul?"), expand it using the context.
6. If the query is ambiguous and you cannot safely resolve it, set needs_clarification=true.
7. NEVER invent information. NEVER guess at entity names not in the query or context.
8. The rewritten_query must be a clear, complete English question suitable for database retrieval.
9. For compound queries requiring multiple pieces of evidence, list each retrieval task in evidence_plan.

Return ONLY valid JSON, no extra text."""


_QU_USER_PROMPT = """Patient query: "{query}"

Known patient entities:
  People: {people}
  Medications: {medications}

Conversation context (last 3 turns):
{context_summary}

Last referenced:
  Person: {last_person}
  Event: {last_event}
  Location: {last_location}
  Date: {last_date}
  Last intent: {last_intent}

Return JSON with these exact fields:
{{
  "intent_hint": "VISIT_RECALL|MEDICATION_ADHERENCE|PERSON_LOOKUP|DAILY_ROUTINE|MEDICATION_SCHEDULE|TEMPORAL_RECALL|GENERAL_CONVERSATION|UNKNOWN",
  "entities": {{"person": null, "medication": null, "location": null}},
  "date_expression": null,
  "resolved_references": {{}},
  "rewritten_query": "...",
  "needs_clarification": false,
  "clarification_question": null,
  "confidence": 0.0,
  "evidence_plan": []
}}"""


async def _run_gemini_qu(
    query: str,
    context: ConversationContext | None,
    reference_date: date | None,
) -> dict[str, Any] | None:
    """
    Calls Gemini for Mode B query understanding.
    Returns parsed JSON dict or None on failure.
    """
    import json as _json
    from app.ai.providers.llm import get_llm_provider
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.GOOGLE_API_KEY or settings.GOOGLE_API_KEY.startswith("your-"):
        return None

    ctx = context
    people_str = ", ".join(ctx.known_people) if (ctx and ctx.known_people) else "(none)"
    meds_str = ", ".join(ctx.known_medications) if (ctx and ctx.known_medications) else "(none)"

    context_lines: list[str] = []
    if ctx and ctx.recent_turns:
        for turn in ctx.recent_turns[-3:]:
            role = turn.get("role", "?")
            content = turn.get("content", "")[:120]
            context_lines.append(f"  {role}: {content}")
    context_summary = "\n".join(context_lines) if context_lines else "  (no prior turns)"

    last_person = (ctx.last_referenced_person or "none") if ctx else "none"
    last_event = (ctx.last_referenced_event or "none") if ctx else "none"
    last_location = (ctx.last_referenced_location or "none") if ctx else "none"
    last_date = (str(ctx.last_referenced_date) if ctx and ctx.last_referenced_date else "none")
    last_intent = (ctx.last_intent.value if ctx and ctx.last_intent else "none")

    prompt = _QU_USER_PROMPT.format(
        query=query,
        people=people_str,
        medications=meds_str,
        context_summary=context_summary,
        last_person=last_person,
        last_event=last_event,
        last_location=last_location,
        last_date=last_date,
        last_intent=last_intent,
    )

    try:
        llm = get_llm_provider()
        raw = await llm.generate(
            prompt=prompt,
            system_instruction=_QU_SYSTEM_PROMPT,
            temperature=0.05,  # Near-deterministic — we want structured output, not creativity
        )
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        return _json.loads(raw)
    except Exception as e:
        logger.warning("[QU] Gemini-assisted query understanding failed: %s", e)
        return None


def _intent_from_str(value: str | None) -> PMEIntent | None:
    """Safely parse an intent string to PMEIntent."""
    if not value:
        return None
    try:
        return PMEIntent(value.lower())
    except ValueError:
        return None


# ── Main Query Understanding Layer ────────────────────────────────────────────

def _is_compound_query(query: str) -> bool:
    """Checks if query contains multiple questions or compound clauses requiring multi-memory retrieval."""
    q_lower = query.lower()
    if re.search(r"\b(?:and|also|plus)\s+(?:what|when|where|who|how|why|did|was|were)\b", q_lower):
        return True
    q_words = re.findall(r"\b(when|where|who|what|how|why)\b", q_lower)
    if len(q_words) >= 2:
        return True
    return False


def _is_malformed_query(query: str) -> bool:
    """Checks if word order is scrambled or malformed."""
    clean = re.sub(r"[^\w\s]", "", query.strip().lower())
    words = clean.split()
    if not words:
        return False
    if words[-1] in {"where", "when", "who", "what", "how", "why"}:
        return True
    if len(words) <= 4:
        has_verb_or_aux = any(
            w in {"did", "does", "do", "is", "are", "was", "were", "go", "went", "come", "came", "visit", "visited", "meet", "met", "eat", "ate", "see", "saw", "take", "took"}
            for w in words
        )
        if not has_verb_or_aux:
            return True
    return False


class QueryUnderstandingLayer:
    """
    Entry point for all query understanding operations.

    Usage:
        qu = QueryUnderstandingLayer()
        result = await qu.understand(
            raw_query="rahul last sunday where",
            context=conversation_context,
            patient_name="Shanti ji",
        )
        # Use result.rewritten_query for PME retrieval
        # If result.needs_clarification: send result.clarification_question to patient
    """

    async def understand(
        self,
        raw_query: str,
        context: ConversationContext | None = None,
        patient_name: str = "the patient",
        reference_date: date | None = None,
    ) -> QueryUnderstanding:
        """
        Analyzes the patient query and returns a QueryUnderstanding object.
        Operates in Mode A (deterministic) first, Mode B (Gemini) if needed,
        Mode C (clarification) if ambiguity cannot be resolved.
        """
        if not raw_query or not raw_query.strip():
            return self._empty_result(raw_query or "", context)

        language = context.language if context else "en"

        # ── Step 1: Spelling Correction ────────────────────────────────────────
        corrected_query, spelling_corrections = _correct_spelling(raw_query, context)

        # ── Step 2: Detect bare follow-up ─────────────────────────────────────
        is_bare = _is_bare_followup(corrected_query)

        if is_bare:
            rewritten, needs_clarification, clarification_q = _resolve_bare_followup(
                corrected_query, context, reference_date
            )
            if needs_clarification:
                clarification_q = self._localize_clarification(
                    clarification_q or "Could you tell me a bit more?", language, context
                )
                return QueryUnderstanding(
                    original_query=raw_query,
                    language=language,
                    intent_hint=context.last_intent if context else None,
                    entities={},
                    date_reference=None,
                    resolved_references=spelling_corrections,
                    rewritten_query=corrected_query,
                    needs_clarification=True,
                    clarification_question=clarification_q,
                    resolution_mode="clarification",
                    confidence=1.0,
                    evidence_plan=[],
                )
            # Successfully resolved bare follow-up deterministically
            date_ref = parse_temporal_context(rewritten, reference_date=reference_date)
            if not date_ref.is_bounded:
                date_ref = self._inherit_date(context, reference_date)
            return QueryUnderstanding(
                original_query=raw_query,
                language=language,
                intent_hint=context.last_intent if context else None,
                entities=self._extract_basic_entities(rewritten, context),
                date_reference=date_ref,
                resolved_references=spelling_corrections,
                rewritten_query=rewritten,
                needs_clarification=False,
                clarification_question=None,
                resolution_mode="deterministic",
                confidence=0.92,
                evidence_plan=[],
            )

        # ── Step 3: Pronoun Resolution ─────────────────────────────────────────
        pronouns_found = _extract_pronouns(corrected_query)
        rewritten_after_pronouns, pronoun_resolutions, pronoun_needs_clarification = (
            _resolve_pronouns(corrected_query, pronouns_found, context)
        )
        all_resolutions = {**spelling_corrections, **pronoun_resolutions}

        if pronoun_needs_clarification:
            if not (_is_compound_query(raw_query) or _is_malformed_query(raw_query)):
                clarification_q = self._localize_clarification(
                    "Who are you referring to?", language, context
                )
                return QueryUnderstanding(
                    original_query=raw_query,
                    language=language,
                    intent_hint=None,
                    entities={},
                    date_reference=None,
                    resolved_references=all_resolutions,
                    rewritten_query=rewritten_after_pronouns,
                    needs_clarification=True,
                    clarification_question=clarification_q,
                    resolution_mode="clarification",
                    confidence=1.0,
                    evidence_plan=[],
                )

        # ── Step 4: Temporal parsing ───────────────────────────────────────────
        temporal = parse_temporal_context(rewritten_after_pronouns, reference_date=reference_date)
        # Inherit date from context if no explicit date found and prior context has one
        if not temporal.is_bounded and context and context.last_referenced_date:
            temporal = parse_temporal_context(
                str(context.last_referenced_date), reference_date=reference_date
            )

        # ── Step 5: Check if deterministic resolution is sufficient ───────────
        # A query is deterministically resolvable when:
        # - The query is now well-formed after corrections and pronoun resolution
        # - It has a clear question structure (not just scrambled words)
        # - No Gemini call is required for structural understanding
        if self._is_well_formed(rewritten_after_pronouns):
            return QueryUnderstanding(
                original_query=raw_query,
                language=language,
                intent_hint=None,  # Will be detected by intent_detector on rewritten query
                entities=self._extract_basic_entities(rewritten_after_pronouns, context),
                date_reference=temporal,
                resolved_references=all_resolutions,
                rewritten_query=rewritten_after_pronouns,
                needs_clarification=False,
                clarification_question=None,
                resolution_mode="deterministic",
                confidence=0.88,
                evidence_plan=[],
            )

        # ── Step 6: Mode B — Gemini-Assisted ──────────────────────────────────
        gemini_result = await _run_gemini_qu(
            query=rewritten_after_pronouns,
            context=context,
            reference_date=reference_date,
        )

        if gemini_result:
            gemini_rewritten = gemini_result.get("rewritten_query", "").strip()
            gemini_needs_clarification = gemini_result.get("needs_clarification", False)
            gemini_clarification = gemini_result.get("clarification_question")
            gemini_confidence = float(gemini_result.get("confidence", 0.75))
            gemini_intent_str = gemini_result.get("intent_hint")
            gemini_entities = gemini_result.get("entities", {})
            gemini_evidence_plan = gemini_result.get("evidence_plan", [])

            # Merge gemini-resolved references with earlier corrections
            gemini_refs = gemini_result.get("resolved_references", {})
            merged_resolutions = {**all_resolutions, **gemini_refs}

            # Parse temporal from gemini result if available
            gemini_date_expr = gemini_result.get("date_expression")
            if gemini_date_expr:
                temporal = parse_temporal_context(gemini_date_expr, reference_date=reference_date)

            if gemini_needs_clarification:
                clarification_q = gemini_clarification or "Could you tell me more?"
                clarification_q = self._localize_clarification(clarification_q, language, context)
                return QueryUnderstanding(
                    original_query=raw_query,
                    language=language,
                    intent_hint=_intent_from_str(gemini_intent_str),
                    entities=gemini_entities,
                    date_reference=temporal,
                    resolved_references=merged_resolutions,
                    rewritten_query=rewritten_after_pronouns,
                    needs_clarification=True,
                    clarification_question=clarification_q,
                    resolution_mode="clarification",
                    confidence=1.0,
                    evidence_plan=[],
                )

            final_query = gemini_rewritten if gemini_rewritten else rewritten_after_pronouns
            return QueryUnderstanding(
                original_query=raw_query,
                language=language,
                intent_hint=_intent_from_str(gemini_intent_str),
                entities=gemini_entities,
                date_reference=temporal,
                resolved_references=merged_resolutions,
                rewritten_query=final_query,
                needs_clarification=False,
                clarification_question=None,
                resolution_mode="llm_assisted",
                confidence=gemini_confidence,
                evidence_plan=gemini_evidence_plan,
            )

        # ── Step 7: Mode B failed — fall back to best deterministic attempt ───
        logger.info("[QU] Gemini unavailable, using best deterministic result for: %r", raw_query)
        return QueryUnderstanding(
            original_query=raw_query,
            language=language,
            intent_hint=context.last_intent if context else None,
            entities=self._extract_basic_entities(rewritten_after_pronouns, context),
            date_reference=temporal,
            resolved_references=all_resolutions,
            rewritten_query=rewritten_after_pronouns,
            needs_clarification=False,
            clarification_question=None,
            resolution_mode="deterministic",
            confidence=0.65,
            evidence_plan=[],
        )

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _empty_result(self, raw_query: str, context: ConversationContext | None) -> QueryUnderstanding:
        return QueryUnderstanding(
            original_query=raw_query,
            language=(context.language if context else "en"),
            intent_hint=None,
            entities={},
            date_reference=None,
            resolved_references={},
            rewritten_query=raw_query,
            needs_clarification=False,
            clarification_question=None,
            resolution_mode="deterministic",
            confidence=0.0,
            evidence_plan=[],
        )

    def _is_well_formed(self, query: str) -> bool:
        """
        Heuristic: the query is well-formed enough for direct intent detection
        without needing a Gemini rewrite.
        """
        if _is_compound_query(query):
            return False
        if _is_malformed_query(query):
            return False
        words = query.strip().split()
        if len(words) >= 5:
            clean_last = re.sub(r"[^\w]", "", words[-1].lower())
            if clean_last in {"where", "when", "who", "what", "how", "why"}:
                return False
            return True
        # Contains a question word at the start/middle and at least one verb
        has_question_word = any(
            w.lower() in {"when", "where", "who", "what", "did", "does", "was", "were",
                          "tell", "show", "how", "why", "is", "are", "has", "have"}
            for w in words
        )
        clean_last = re.sub(r"[^\w]", "", words[-1].lower())
        if has_question_word and clean_last not in {"where", "when", "who", "what", "how", "why"} and len(words) >= 3:
            return True
        return False

    def _inherit_date(
        self,
        context: ConversationContext | None,
        reference_date: date | None,
    ) -> TemporalContext | None:
        """Inherits the last referenced date from context if available."""
        if context and context.last_referenced_date:
            return parse_temporal_context(
                str(context.last_referenced_date), reference_date=reference_date
            )
        return None

    def _extract_basic_entities(
        self, query: str, context: ConversationContext | None
    ) -> dict[str, Any]:
        """Extracts named entities by matching against known patient people/medications."""
        entities: dict[str, Any] = {}
        if not context:
            return entities
        q_lower = query.lower()
        for name in context.known_people:
            if name.lower() in q_lower:
                entities.setdefault("person", name)
                break
        for med in context.known_medications:
            if med.lower() in q_lower:
                entities.setdefault("medication", med)
                break
        return entities

    def _localize_clarification(
        self,
        question_en: str,
        language: str,
        context: ConversationContext | None,
    ) -> str:
        """
        Localizes the clarification question into the patient's language.
        Provides deterministic translations for standard clarification phrases in NE languages.
        """
        if not language or language.lower().startswith("en"):
            return question_en

        lang_prefix = language.split("-")[0].lower()

        clarifications: dict[str, dict[str, str]] = {
            "as": {
                "who are you referring to?": "আপুনি কাৰ বিষয়ে সুধিছে?",
                "could you tell me a bit more about what you'd like to know?": "আপুনি কি জানিব বিচাৰিছে আৰু অলপ ক'ব পাৰিবনে?",
                "what would you like to know about?": "আপুনি কিহৰ বিষয়ে জানিব বিচাৰিছে?",
                "who are you asking about?": "আপুনি কাৰ কথা সুধিছে?",
            },
            "lus": {
                "who are you referring to?": "Tu nge i sawi tum?",
                "could you tell me a bit more about what you'd like to know?": "Khawngaihin i hriat duh zawk min hrilh belh thei em?",
                "what would you like to know about?": "Eng chungchang nge i hriat duh?",
                "who are you asking about?": "Tu chungchang nge i zawh?",
            },
            "kha": {
                "who are you referring to?": "Mano ba phi mut ban kylli?",
                "could you tell me a bit more about what you'd like to know?": "Phi lah ban batai shuh shuh ia kaei ba phi kwah ban tip?",
                "what would you like to know about?": "Kaei ba phi kwah ban tip?",
                "who are you asking about?": "Shaphang mano ba phi kylli?",
            },
            "hi": {
                "who are you referring to?": "आप किसके बारे में पूछ रहे हैं?",
                "could you tell me a bit more about what you'd like to know?": "क्या आप थोड़ा और बता सकते हैं कि आप क्या जानना चाहते हैं?",
                "what would you like to know about?": "आप किस बारे में जानना चाहते हैं?",
                "who are you asking about?": "आप किसके बारे में पूछ रहे हैं?",
            },
        }

        lang_dict = clarifications.get(lang_prefix)
        if lang_dict:
            clean_q = question_en.strip().lower()
            if clean_q in lang_dict:
                return lang_dict[clean_q]

        return question_en


# ── Module-level singleton ────────────────────────────────────────────────────

_qu_layer: QueryUnderstandingLayer | None = None


def get_query_understanding_layer() -> QueryUnderstandingLayer:
    """Returns a shared QueryUnderstandingLayer instance (stateless, safe to share)."""
    global _qu_layer
    if _qu_layer is None:
        _qu_layer = QueryUnderstandingLayer()
    return _qu_layer
