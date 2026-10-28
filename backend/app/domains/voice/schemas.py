"""
CogniCompanion — Voice / Assistant Domain Schemas
===================================================
Pydantic v2 schemas for Assistant queries, Grounded Responses, and Conversations.
"""

from datetime import datetime
import uuid

from pydantic import BaseModel, Field


# ── Turn / Message Schemas ───────────────────────────────────────────────────

class AskAssistantRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000, description="Patient spoken or typed query.")
    conversation_id: uuid.UUID | None = Field(
        default=None,
        description="Optional ongoing conversation ID. Creates a new session if omitted."
    )
    language_code: str = Field(default="en", max_length=10)
    image_base64: str | None = Field(
        default=None,
        description="Optional base64-encoded image for multimodal visual grounding."
    )


class ConfidenceInfo(BaseModel):
    score: float
    level: str  # "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN"
    factors: dict[str, float] | None = None


class GroundedSource(BaseModel):
    source_type: str  # "memory" | "person" | "medication" | "routine" | "event" | "game_session" | "cognitive_metric" | "daily_statistic"
    id: str
    title: str
    summary: str | None = None
    date: str | None = None
    details: str | None = None


class AskAssistantResponse(BaseModel):
    conversation_id: uuid.UUID
    answer: str
    reply: str
    intent: str
    confidence: float
    confidence_info: ConfidenceInfo
    sources: list[GroundedSource] = []
    grounded: bool = True
    audio_base64: str | None = None
    created_at: datetime


class TranscribeAudioResponse(BaseModel):
    transcript: str
    language_code: str = "en"


class SynthesizeSpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language_code: str = "en-IN"
    speaking_rate: float = Field(default=0.9, ge=0.5, le=2.0)


class SynthesizeSpeechResponse(BaseModel):
    audio_base64: str
    format: str = "mp3"


class TranscriptPayload(BaseModel):
    text: str


class AssistantPayload(BaseModel):
    answer: str
    reply: str
    intent: str
    grounded: bool
    confidence: ConfidenceInfo
    sources: list[GroundedSource] = []


class AudioPayload(BaseModel):
    available: bool
    format: str = "mp3"
    audio_base64: str | None = None


class VoiceConverseResponse(BaseModel):
    conversation_id: uuid.UUID
    transcript: str
    transcript_info: TranscriptPayload | None = None
    answer: str
    reply: str
    intent: str
    confidence: float
    confidence_info: ConfidenceInfo
    assistant: AssistantPayload | None = None
    sources: list[GroundedSource] = []
    grounded: bool = True
    audio: AudioPayload | None = None
    audio_base64: str | None = None
    created_at: datetime


# ── Conversation History Schemas ─────────────────────────────────────────────

class MessageItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    role: str
    content: str
    intent_type: str | None
    confidence_score: float | None
    sources_json: list[dict] | dict | None = None
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    patient_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    language_code: str | None
    message_count: int
    messages: list[MessageItemResponse] = []
