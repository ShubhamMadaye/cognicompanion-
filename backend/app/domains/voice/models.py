"""
CogniCompanion — Voice / Assistant Domain Models
===================================================
SQLAlchemy 2.0 ORM models for the conversational assistant:
  - conversations        (a session of user–assistant interaction)
  - conversation_messages (individual turns with confidence + sources)

Also includes:
  - memory_embeddings   (pgvector embeddings for semantic retrieval)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Cross-dialect JSON type: JSONB on PostgreSQL, JSON on SQLite (tests)
_JSONB = JSON().with_variant(JSONB(), "postgresql")

try:
    from pgvector.sqlalchemy import Vector
    _PGVECTOR_AVAILABLE = True
except ImportError:
    Vector = None  # type: ignore[assignment,misc]
    _PGVECTOR_AVAILABLE = False

from app.core.database import Base


# ── conversations ──────────────────────────────────────────────────────────────

class Conversation(Base):
    """
    A session of interaction between a patient and the AI assistant.

    Grouping messages into conversations allows:
      - Multi-turn context ("When did Rahul visit before *that*?")
      - Session-level analytics (avg confidence, queries per session)
      - The Explainability Panel to show sources per conversation
    """
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)  # e.g. "en-IN"
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage", back_populates="conversation", cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at"
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} patient_id={self.patient_id}>"


# ── conversation_messages ─────────────────────────────────────────────────────

class ConversationMessage(Base):
    """
    A single turn in a conversation — either patient query or assistant response.

    For ASSISTANT messages:
      - intent_type:     what the PME detected (e.g. PERSON_QUERY)
      - confidence_score: 0.0–1.0 (drives Confidence & Safety Layer)
      - sources_json:    list of source references for the Explainability Panel
                         Example: [{"type": "memory", "id": "...", "title": "Rahul's visit"}]

    No patient data is logged at the application layer (blueprint Section 11).
    sources_json stores references (IDs), not raw personal data.
    """
    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "patient" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # STT input or TTS output file reference

    # ── Assistant-only fields ─────────────────────────────────────────────────
    intent_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g. "PERSON_QUERY", "MEDICATION_QUERY"
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0–1.0
    sources_json: Mapped[dict | None] = mapped_column(_JSONB, nullable=True)  # Explainability
    llm_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ConversationMessage id={self.id} role={self.role!r} confidence={self.confidence_score}>"


# ── memory_embeddings ─────────────────────────────────────────────────────────

class MemoryEmbedding(Base):
    """
    pgvector embedding for a Memory's description text.

    Enables semantic search in the Personalized Memory Engine:
      "Tell me about the time Rahul brought sweets."
      → cosine similarity search over embeddings
      → retrieve top-k matching memories
      → pass to Context Builder

    model_version: Stored so embeddings can be re-generated
                   if the embedding model is upgraded.
    embedding:     768-dim for Gemini text-embedding-004.
                   Stored as vector(768) via pgvector SQLAlchemy type.
                   Falls back to nullable column if pgvector not installed.
    """
    __tablename__ = "memory_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    # pgvector column: 768-dim for Gemini text-embedding-004
    # Populated by Phase 4 embedding generation handler
    embedding = mapped_column(
        Vector(768) if _PGVECTOR_AVAILABLE else Text,  # type: ignore[arg-type]
        nullable=True,
    )
    embedding_text: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # The text that was embedded (for re-generation auditing)
    model_version: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g. "models/text-embedding-004"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    memory: Mapped["Memory"] = relationship(  # type: ignore[name-defined]
        "app.domains.memories.models.Memory", back_populates="embedding"
    )

    def __repr__(self) -> str:
        return f"<MemoryEmbedding id={self.id} memory_id={self.memory_id}>"
