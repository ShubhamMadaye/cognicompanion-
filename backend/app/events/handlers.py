"""
CogniCompanion — Event Handlers
==================================
Subscribe domain handlers to events on the event bus.

Called from app/main.py at startup via register_event_handlers().
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.bus import (
    DomainEvent,
    EventBus,
    GameSessionCompletedEvent,
    MemoryCreatedEvent,
    MedicationTakenEvent,
)

logger = logging.getLogger(__name__)


# ── Memory Created Handlers ───────────────────────────────────────────────────

async def handle_memory_created_generate_embedding(event: DomainEvent, db_session: AsyncSession | None = None) -> None:
    """
    When a new Memory is created, asynchronously generate and store its embedding for semantic search.
    Embedding failure must never block or raise unhandled exceptions.
    """
    assert isinstance(event, MemoryCreatedEvent)
    from app.ai.providers.embeddings import get_embedding_provider
    from app.core.config import get_settings
    from app.core.database import AsyncSessionLocal
    from app.domains.memories.models import Memory
    from app.domains.voice.models import MemoryEmbedding
    from sqlalchemy import select

    settings = get_settings()
    if not settings.GOOGLE_API_KEY or settings.GOOGLE_API_KEY.startswith("your_"):
        logger.debug("Google API key not configured — skipping immediate embedding generation for memory_id=%s", event.memory_id)
        return

    async def _process_with_session(session: AsyncSession) -> None:
        res = await session.execute(select(Memory).where(Memory.id == event.memory_id))
        memory = res.scalar_one_or_none()
        if not memory:
            return

        text_to_embed = f"{memory.title}\n{memory.description or ''}".strip()
        if not text_to_embed:
            return

        provider = get_embedding_provider()
        vector = await provider.embed(text_to_embed)

        # Check if an embedding row already exists
        emb_res = await session.execute(
            select(MemoryEmbedding).where(MemoryEmbedding.memory_id == memory.id)
        )
        emb_record = emb_res.scalar_one_or_none()

        if emb_record:
            emb_record.embedding = vector
            emb_record.embedding_text = text_to_embed
            emb_record.model_version = settings.EMBEDDING_MODEL
        else:
            new_emb = MemoryEmbedding(
                memory_id=memory.id,
                embedding=vector,
                embedding_text=text_to_embed,
                model_version=settings.EMBEDDING_MODEL,
            )
            session.add(new_emb)

        await session.commit()
        logger.info("Successfully stored embedding for memory_id=%s", memory.id)

    try:
        if db_session is not None:
            await _process_with_session(db_session)
        else:
            async with AsyncSessionLocal() as session:
                await _process_with_session(session)
    except Exception as e:
        logger.warning("Embedding generation background job failed for memory_id=%s: %s", event.memory_id, e)


async def handle_memory_created_update_timeline(event: DomainEvent) -> None:
    """
    Intentional no-op — architectural decision (Phase 2).

    Memories are stored independently from the timeline. Event-type memories
    (VISIT, OUTING, APPOINTMENT) are surfaced in the unified day view via a
    live query in TimelineService.get_day_timeline(), NOT by creating a
    duplicate timeline Event row here.

    Contextual/chronological timelines are generated dynamically by the patient
    voice interface when they ask a chronological question (Phase 3+).
    """
    assert isinstance(event, MemoryCreatedEvent)
    logger.debug(
        "Memory created (memory_id=%s, patient_id=%s) — timeline surfaced via live query",
        event.memory_id,
        event.patient_id,
    )


# ── Game Completed Handlers ───────────────────────────────────────────────────

async def handle_game_completed_update_analytics(event: DomainEvent) -> None:
    """Update daily statistics and CPI when a game session completes. Phase 8 implementation."""
    assert isinstance(event, GameSessionCompletedEvent)
    logger.info(
        "TODO (Phase 8): Update CPI for session_id=%s patient_id=%s accuracy=%.2f",
        event.session_id,
        event.patient_id,
        event.accuracy,
    )


async def handle_game_completed_update_timeline(event: DomainEvent) -> None:
    """Create a GAME_SESSION timeline event when a game completes. Phase 2 implementation."""
    assert isinstance(event, GameSessionCompletedEvent)
    logger.info(
        "TODO (Phase 2): Create game timeline event for session_id=%s", event.session_id
    )


# ── Medication Taken Handlers ─────────────────────────────────────────────────

async def handle_medication_taken_update_dashboard(event: DomainEvent) -> None:
    """Update caregiver dashboard medication status. Phase 9 implementation."""
    assert isinstance(event, MedicationTakenEvent)
    logger.info(
        "TODO (Phase 9): Update medication dashboard for patient_id=%s", event.patient_id
    )


# ── Registration ──────────────────────────────────────────────────────────────

def register_event_handlers(bus: EventBus) -> None:
    """
    Register all event handlers.
    Called once at application startup.
    """
    # Memory events
    bus.subscribe(MemoryCreatedEvent, handle_memory_created_generate_embedding)
    bus.subscribe(MemoryCreatedEvent, handle_memory_created_update_timeline)

    # Game events
    bus.subscribe(GameSessionCompletedEvent, handle_game_completed_update_analytics)
    bus.subscribe(GameSessionCompletedEvent, handle_game_completed_update_timeline)

    # Medication events
    bus.subscribe(MedicationTakenEvent, handle_medication_taken_update_dashboard)

    logger.info("Event handlers registered.")
