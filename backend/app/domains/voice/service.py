"""
CogniCompanion — Voice / Assistant Domain Service
===================================================
Orchestrates Personalized Memory Grounding, Intent-Aware Retrieval,
Confidence Calculation, LLM Generation, and Conversation Turn Logging.
"""

from datetime import date as date_type, datetime, timezone
from typing import Sequence
import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.memory_engine import MemoryEngine
from app.ai.memory_engine.intent_detector import PMEIntent
from app.ai.memory_engine.query_understanding import ConversationContext
from app.core.config import get_settings
from app.domains.patients.models import Patient
from app.domains.voice.models import Conversation, ConversationMessage
from app.domains.voice.schemas import (
    AskAssistantRequest,
    AskAssistantResponse,
    ConfidenceInfo,
    GroundedSource,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class VoiceAssistantService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_or_create_conversation(
        self, patient_id: uuid.UUID, conversation_id: uuid.UUID | None, language_code: str
    ) -> Conversation:
        if conversation_id:
            result = await self._db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.patient_id == patient_id,
                )
            )
            conv = result.scalar_one_or_none()
            if conv:
                return conv

        conv = Conversation(
            patient_id=patient_id,
            language_code=language_code,
            started_at=datetime.now(timezone.utc),
        )
        self._db.add(conv)
        await self._db.flush()
        return conv

    async def process_turn(
        self, patient_id: uuid.UUID, request: AskAssistantRequest
    ) -> AskAssistantResponse:
        """
        Executes grounded memory retrieval and generates a compassionate, reassuring response.
        Flow:
          1. Detect intent and entities with central temporal context
          2. Intent-specific DB query (Structured Retriever + Semantic Retriever)
          3. Deterministic confidence scoring & sources (Confidence Engine)
          4. Grounded prompt & fallback construction (Context Builder)
          5. Response synthesis (Response Generator with configured Gemini model)
          6. Persist conversation turn
        """
        conv = await self.get_or_create_conversation(
            patient_id, request.conversation_id, request.language_code
        )

        # Fetch patient profile name for personalization
        pat_res = await self._db.execute(
            select(Patient).options(selectinload(Patient.user)).where(Patient.id == patient_id)
        )
        patient = pat_res.scalar_one_or_none()
        # Patient name must always come from the authenticated patient record.
        # A neutral fallback is used only when the record is temporarily unavailable.
        # DO NOT hardcode a specific patient's name here.
        patient_name = (patient.user.full_name if (patient and patient.user) else None) or "the patient"

        # Build conversation context from last 4 turns (rebuilt from DB each turn
        # — never cached in-process memory for strict patient isolation)
        conversation_context = await self._build_conversation_context(
            patient_id=patient_id,
            conversation_id=conv.id,
            language_code=request.language_code,
            patient=patient,
        )

        # Delegate grounded retrieval & response generation to MemoryEngine
        engine = MemoryEngine(self._db)
        pme_result = await engine.process_query(
            patient_id=patient_id,
            query=request.query,
            patient_name=patient_name,
            language_code=request.language_code,
            image_base64=request.image_base64,
            conversation_context=conversation_context,
        )

        now = datetime.now(timezone.utc)

        # 6. Persist Turn
        user_msg = ConversationMessage(
            conversation_id=conv.id,
            role="patient",
            content=request.query,
            created_at=now,
        )
        asst_msg = ConversationMessage(
            conversation_id=conv.id,
            role="assistant",
            content=pme_result.answer,
            intent_type=pme_result.intent.value,
            confidence_score=pme_result.confidence_score,
            sources_json=[s.model_dump() for s in pme_result.sources] if pme_result.sources else None,
            llm_model_used=pme_result.model_used,
            created_at=now,
        )
        self._db.add_all([user_msg, asst_msg])
        conv.message_count += 2
        await self._db.flush()

        rounded_score = round(pme_result.confidence_score, 2)

        return AskAssistantResponse(
            conversation_id=conv.id,
            answer=pme_result.answer,
            reply=pme_result.answer,
            intent=pme_result.intent.value,
            confidence=rounded_score,
            confidence_info=ConfidenceInfo(
                score=rounded_score,
                level=pme_result.confidence_level,
                factors=pme_result.confidence_factors,
            ),
            sources=pme_result.sources,
            grounded=bool(pme_result.sources),
            created_at=now,
        )

    async def list_conversations(
        self, patient_id: uuid.UUID, limit: int = 20
    ) -> Sequence[Conversation]:
        result = await self._db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.patient_id == patient_id)
            .order_by(Conversation.started_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def _build_conversation_context(
        self,
        patient_id: uuid.UUID,
        conversation_id: uuid.UUID,
        language_code: str,
        patient: Patient | None,
    ) -> ConversationContext:
        """
        Builds a ConversationContext from the last 4 turns of the current conversation.
        Always rebuilt from DB — never cached in-process memory.
        Patient isolation is enforced at query level (conversation_id + patient_id).
        """
        # Load last 4 messages for this conversation
        msgs_result = await self._db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(8)  # 4 turns = 8 messages (patient + assistant per turn)
        )
        recent_messages = list(reversed(msgs_result.scalars().all()))

        recent_turns: list[dict] = []
        last_intent: PMEIntent | None = None
        last_referenced_person: str | None = None
        last_referenced_date: date_type | None = None
        last_referenced_event: str | None = None
        last_referenced_location: str | None = None
        last_pme_evidence: list[str] = []

        for msg in recent_messages:
            turn: dict = {"role": msg.role, "content": msg.content[:200]}
            if msg.role == "assistant" and msg.intent_type:
                try:
                    turn_intent = PMEIntent(msg.intent_type.lower())
                    turn["intent"] = turn_intent.value
                    last_intent = turn_intent
                except ValueError:
                    pass
            if msg.sources_json:
                sources = msg.sources_json if isinstance(msg.sources_json, list) else []
                for src in sources:
                    if isinstance(src, dict):
                        if src.get("person"):
                            last_referenced_person = src["person"]
                            turn["person"] = last_referenced_person
                        if src.get("title"):
                            last_referenced_event = src["title"]
            recent_turns.append(turn)

        # Build known entities from patient data (for spelling correction)
        known_people_set: set[str] = set()
        known_medications_set: set[str] = set()

        for msg in recent_messages:
            if msg.sources_json:
                sources = msg.sources_json if isinstance(msg.sources_json, list) else []
                for src in sources:
                    if isinstance(src, dict) and src.get("person"):
                        known_people_set.add(src["person"])

        if patient_id:
            from app.domains.memories.models import Person
            from app.domains.timeline.models import Medication

            try:
                people_res = await self._db.execute(
                    select(Person.name).where(
                        Person.patient_id == patient_id, Person.is_active == True
                    )
                )
                for p_name in people_res.scalars().all():
                    if p_name:
                        known_people_set.add(p_name.strip())
            except Exception as e:
                logger.warning("[VoiceService] Failed to load patient people roster: %s", e)

            try:
                meds_res = await self._db.execute(
                    select(Medication.name).where(Medication.patient_id == patient_id)
                )
                for m_name in meds_res.scalars().all():
                    if m_name:
                        known_medications_set.add(m_name.strip())
            except Exception as e:
                logger.warning("[VoiceService] Failed to load patient medications: %s", e)

        known_people = list(known_people_set)
        known_medications = list(known_medications_set)

        return ConversationContext(
            conversation_id=conversation_id,
            patient_id=patient_id,
            language=language_code,
            recent_turns=recent_turns,
            last_intent=last_intent,
            last_referenced_person=last_referenced_person,
            last_referenced_event=last_referenced_event,
            last_referenced_location=last_referenced_location,
            last_referenced_date=last_referenced_date,
            last_pme_evidence=last_pme_evidence,
            known_people=known_people,
            known_medications=known_medications,
        )
