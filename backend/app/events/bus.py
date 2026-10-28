"""
CogniCompanion — Internal Event Bus
======================================
A lightweight in-process event bus for domain events.

This avoids coupling domains directly to each other.
Example: when a GameSession completes, it publishes GameCompletedEvent.
The analytics handler updates CPI; the timeline handler creates an Event entry.

No external broker (Kafka, RabbitMQ) needed for MVP.
If we scale beyond a single process later, swap this for a broker adapter.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# ── Base Event ────────────────────────────────────────────────────────────────

@dataclass
class DomainEvent:
    """Base class for all domain events."""
    occurred_at: datetime = field(default_factory=datetime.utcnow)


# ── Domain Events ─────────────────────────────────────────────────────────────

@dataclass
class MemoryCreatedEvent(DomainEvent):
    """Published when a new Memory is created by a caregiver."""
    memory_id: str = ""
    patient_id: str = ""
    memory_type: str = ""


@dataclass
class GameSessionCompletedEvent(DomainEvent):
    """Published when a GameSession reaches status=COMPLETED."""
    session_id: str = ""
    patient_id: str = ""
    game_type: str = ""
    accuracy: float = 0.0
    cpi_contribution: float = 0.0


@dataclass
class MedicationTakenEvent(DomainEvent):
    """Published when a medication adherence log entry is recorded as taken."""
    adherence_log_id: str = ""
    medication_id: str = ""
    patient_id: str = ""


@dataclass
class ConversationEndedEvent(DomainEvent):
    """Published when an assistant conversation session ends."""
    conversation_id: str = ""
    patient_id: str = ""
    message_count: int = 0


# ── Event Bus ─────────────────────────────────────────────────────────────────

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    """
    Simple in-process async event bus.

    Handlers are registered per event type.
    Publishing an event calls all registered handlers concurrently.
    Handler failures are logged but do NOT propagate — they must not
    break the primary request/response flow.
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: EventHandler) -> None:
        """Register a handler for an event type."""
        self._handlers[event_type].append(handler)
        logger.debug("Subscribed %s to %s", handler.__name__, event_type.__name__)

    async def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to all registered handlers.

        Handlers run concurrently via asyncio.gather().
        Individual handler failures are caught and logged.
        """
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            return

        async def _safe_call(handler: EventHandler, evt: DomainEvent) -> None:
            try:
                await handler(evt)
            except Exception:
                logger.exception(
                    "Event handler %s failed for event %s",
                    handler.__name__,
                    type(evt).__name__,
                )

        await asyncio.gather(*(_safe_call(h, event) for h in handlers))


# Singleton event bus — imported by all domains
event_bus = EventBus()
