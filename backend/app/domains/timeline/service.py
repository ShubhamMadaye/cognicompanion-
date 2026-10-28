"""
CogniCompanion — Timeline Domain Service
==========================================
Business logic for Medications, Routines, Events, and the combined timeline.
"""

import uuid
from datetime import date, datetime, timezone
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.domains.memories.models import Memory, MemoryType
from app.domains.timeline.models import (
    Event,
    Medication,
    MedicationAdherenceLog,
    Routine,
)
from app.domains.timeline.schemas import (
    CreateEventRequest,
    CreateMedicationRequest,
    CreateRoutineRequest,
    LogMedicationRequest,
    TimelineEntryResponse,
    UpdateEventRequest,
    UpdateMedicationRequest,
    UpdateRoutineRequest,
)
from app.domains.patients.models import User
from app.events.bus import MedicationTakenEvent, event_bus


# ── Medications ───────────────────────────────────────────────────────────────

class MedicationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self, patient_id: uuid.UUID, data: CreateMedicationRequest
    ) -> Medication:
        med = Medication(
            patient_id=patient_id,
            name=data.name,
            dosage=data.dosage,
            frequency=data.frequency,
            timing=data.timing,
            scheduled_time=data.scheduled_time,
            start_date=data.start_date,
            end_date=data.end_date,
            notes=data.notes,
        )
        self._db.add(med)
        await self._db.flush()
        return med

    async def list_active(self, patient_id: uuid.UUID) -> Sequence[Medication]:
        result = await self._db.execute(
            select(Medication)
            .where(Medication.patient_id == patient_id, Medication.is_active == True)  # noqa: E712
            .order_by(Medication.name)
        )
        return result.scalars().all()

    async def get(
        self, patient_id: uuid.UUID, medication_id: uuid.UUID
    ) -> Medication:
        result = await self._db.execute(
            select(Medication).where(
                Medication.id == medication_id,
                Medication.patient_id == patient_id,
            )
        )
        med = result.scalar_one_or_none()
        if not med:
            raise NotFoundError("Medication")
        return med

    async def update(
        self,
        patient_id: uuid.UUID,
        medication_id: uuid.UUID,
        data: UpdateMedicationRequest,
    ) -> Medication:
        med = await self.get(patient_id, medication_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(med, field, value)
        await self._db.flush()
        return med

    async def log_adherence(
        self,
        patient_id: uuid.UUID,
        medication_id: uuid.UUID,
        data: LogMedicationRequest,
        confirmed_by: User,
    ) -> MedicationAdherenceLog:
        med = await self.get(patient_id, medication_id)

        # One log per medication per day
        existing = await self._db.execute(
            select(MedicationAdherenceLog).where(
                MedicationAdherenceLog.medication_id == medication_id,
                MedicationAdherenceLog.log_date == data.log_date,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError("Adherence log already exists for this date")

        log = MedicationAdherenceLog(
            medication_id=medication_id,
            log_date=data.log_date,
            taken=data.taken,
            taken_at=data.taken_at,
            confirmed_by=confirmed_by.id,
            notes=data.notes,
        )
        self._db.add(log)
        await self._db.flush()

        if data.taken:
            await event_bus.publish(
                MedicationTakenEvent(
                    adherence_log_id=str(log.id),
                    medication_id=str(medication_id),
                    patient_id=str(patient_id),
                )
            )
        return log


# ── Routines ──────────────────────────────────────────────────────────────────

class RoutineService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self, patient_id: uuid.UUID, data: CreateRoutineRequest
    ) -> Routine:
        routine = Routine(
            patient_id=patient_id,
            title=data.title,
            description=data.description,
            category=data.category,
            scheduled_time=data.scheduled_time,
            days_of_week=data.days_of_week,
            icon_emoji=data.icon_emoji,
        )
        self._db.add(routine)
        await self._db.flush()
        return routine

    async def list_active(self, patient_id: uuid.UUID) -> Sequence[Routine]:
        result = await self._db.execute(
            select(Routine)
            .where(Routine.patient_id == patient_id, Routine.is_active == True)  # noqa: E712
            .order_by(Routine.scheduled_time)
        )
        return result.scalars().all()

    async def get(
        self, patient_id: uuid.UUID, routine_id: uuid.UUID
    ) -> Routine:
        result = await self._db.execute(
            select(Routine).where(
                Routine.id == routine_id, Routine.patient_id == patient_id
            )
        )
        routine = result.scalar_one_or_none()
        if not routine:
            raise NotFoundError("Routine")
        return routine

    async def update(
        self,
        patient_id: uuid.UUID,
        routine_id: uuid.UUID,
        data: UpdateRoutineRequest,
    ) -> Routine:
        routine = await self.get(patient_id, routine_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(routine, field, value)
        await self._db.flush()
        return routine


# ── Events ────────────────────────────────────────────────────────────────────

class EventService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        patient_id: uuid.UUID,
        data: CreateEventRequest,
        created_by: User,
    ) -> Event:
        event = Event(
            patient_id=patient_id,
            created_by=created_by.id,
            event_type=data.event_type,
            title=data.title,
            description=data.description,
            location=data.location,
            start_time=data.start_time,
            end_time=data.end_time,
            icon_emoji=data.icon_emoji,
            linked_memory_id=data.linked_memory_id,
        )
        self._db.add(event)
        await self._db.flush()
        return event

    async def list_events(
        self,
        patient_id: uuid.UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 50,
    ) -> Sequence[Event]:
        query = select(Event).where(Event.patient_id == patient_id)
        if start_date:
            query = query.where(Event.start_time >= datetime(start_date.year, start_date.month, start_date.day))
        if end_date:
            import datetime as dt
            end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
            query = query.where(Event.start_time <= end_dt)
        query = query.order_by(Event.start_time.desc()).limit(limit)
        result = await self._db.execute(query)
        return result.scalars().all()

    async def get(
        self, patient_id: uuid.UUID, event_id: uuid.UUID
    ) -> Event:
        result = await self._db.execute(
            select(Event).where(Event.id == event_id, Event.patient_id == patient_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            raise NotFoundError("Event")
        return event

    async def update(
        self,
        patient_id: uuid.UUID,
        event_id: uuid.UUID,
        data: UpdateEventRequest,
    ) -> Event:
        event = await self.get(patient_id, event_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(event, field, value)
        await self._db.flush()
        return event

    async def delete(self, patient_id: uuid.UUID, event_id: uuid.UUID) -> None:
        event = await self.get(patient_id, event_id)
        await self._db.delete(event)


# ── Combined Timeline View ────────────────────────────────────────────────────

class TimelineService:
    """
    Assembles a unified day view from multiple domain tables.
    Returns entries sorted chronologically for display in the Flutter day-view widget.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._med_svc = MedicationService(db)
        self._routine_svc = RoutineService(db)
        self._event_svc = EventService(db)

    async def get_day_timeline(
        self,
        patient_id: uuid.UUID,
        day: date,
    ) -> list[TimelineEntryResponse]:
        """
        Returns all timeline items for a given day:
        - Routines active on this day of week
        - Medications (active, with adherence status)
        - Events starting on this day
        """
        entries: list[TimelineEntryResponse] = []

        # Day-of-week bitmask: Monday=0→bit 1, ..., Sunday=6→bit 64
        dow_bit = 1 << day.weekday()

        # Routines
        routines = await self._routine_svc.list_active(patient_id)
        for r in routines:
            if r.days_of_week & dow_bit:
                ts = datetime.combine(day, r.scheduled_time, tzinfo=timezone.utc)
                entries.append(
                    TimelineEntryResponse(
                        kind="routine",
                        id=r.id,
                        title=r.title,
                        description=r.description,
                        icon_emoji=r.icon_emoji or "📋",
                        timestamp=ts,
                        display_time=r.scheduled_time.strftime("%H:%M"),
                        metadata={"category": r.category.value},
                    )
                )

        # Medications
        medications = await self._med_svc.list_active(patient_id)
        for m in medications:
            if m.start_date and m.start_date > day:
                continue
            if m.end_date and m.end_date < day:
                continue
            sched_time = m.scheduled_time or datetime.now(timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0).time()
            ts = datetime.combine(day, sched_time, tzinfo=timezone.utc)

            # Check today's adherence
            log_result = await self._db.execute(
                select(MedicationAdherenceLog).where(
                    MedicationAdherenceLog.medication_id == m.id,
                    MedicationAdherenceLog.log_date == day,
                )
            )
            log = log_result.scalar_one_or_none()

            entries.append(
                TimelineEntryResponse(
                    kind="medication",
                    id=m.id,
                    title=m.name,
                    description=m.dosage,
                    icon_emoji="💊",
                    timestamp=ts,
                    display_time=sched_time.strftime("%H:%M"),
                    metadata={
                        "frequency": m.frequency.value,
                        "timing": m.timing.value,
                        "taken": log.taken if log else None,
                        "taken_at": log.taken_at.isoformat() if log and log.taken_at else None,
                    },
                )
            )

        # Events
        events = await self._event_svc.list_events(
            patient_id, start_date=day, end_date=day
        )
        for e in events:
            entries.append(
                TimelineEntryResponse(
                    kind="event",
                    id=e.id,
                    title=e.title,
                    description=e.description,
                    icon_emoji=e.icon_emoji or "📅",
                    timestamp=e.start_time,
                    display_time=e.start_time.strftime("%H:%M"),
                    metadata={
                        "event_type": e.event_type.value,
                        "location": e.location,
                        "end_time": e.end_time.isoformat() if e.end_time else None,
                        "linked_memory_id": str(e.linked_memory_id) if e.linked_memory_id else None,
                    },
                )
            )

        # Event-type memories (VISIT, OUTING, APPOINTMENT) for this day.
        # Memories are stored independently; they surface here as read-only cards.
        # Contextual/chronological timelines are built dynamically by the voice
        # interface in Phase 3+ — not by creating duplicate Event rows.
        _EVENT_MEMORY_TYPES = {MemoryType.VISIT, MemoryType.OUTING, MemoryType.APPOINTMENT}
        memory_result = await self._db.execute(
            select(Memory)
            .where(
                Memory.patient_id == patient_id,
                Memory.event_date == day,
                Memory.memory_type.in_(_EVENT_MEMORY_TYPES),
            )
            .order_by(Memory.created_at)
        )
        for mem in memory_result.scalars().all():
            _MEMORY_ICONS: dict[MemoryType, str] = {
                MemoryType.VISIT: "👥",
                MemoryType.OUTING: "🚶",
                MemoryType.APPOINTMENT: "🏥",
            }
            ts = datetime(
                day.year, day.month, day.day,
                tzinfo=timezone.utc,
            )
            entries.append(
                TimelineEntryResponse(
                    kind="memory",
                    id=mem.id,
                    title=mem.title,
                    description=mem.description,
                    icon_emoji=_MEMORY_ICONS.get(mem.memory_type, "📝"),
                    timestamp=ts,
                    display_time="All day",
                    metadata={
                        "memory_type": mem.memory_type.value,
                        "is_significant": mem.is_significant,
                        "location": mem.location,
                    },
                )
            )

        # Sort chronologically
        entries.sort(key=lambda x: x.timestamp)
        return entries
