"""
CogniCompanion — PME Structured Retriever
=========================================
Executes intent-specific, strictly patient-scoped SQL queries against PostgreSQL/SQLite for:
  - People & Relationships
  - Memories (Visits, Outings)
  - Timeline Routines & Events
  - Medications & Adherence Logs
  - Game Sessions & Performance Metrics
  - Daily Statistics & Cognitive Metrics (CPI)

Enforces strict date and timing boundaries and eliminates N+1 queries.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.memories.models import Memory, MemoryType, Person
from app.domains.timeline.models import (
    Event,
    EventType,
    Medication,
    MedicationAdherenceLog,
    MedicationTiming,
    Routine,
    RoutineCategory,
)
from app.domains.games.models import Game, GameSession
from app.domains.analytics.models import DailyStatistic, CognitiveMetric
from app.ai.memory_engine.temporal_parser import TemporalContext


class StructuredRetriever:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def retrieve_person(
        self, patient_id: uuid.UUID, name_hint: str | None = None
    ) -> dict[str, Any]:
        """
        Retrieves matching Person record(s) strictly for the authenticated patient.
        """
        stmt = (
            select(Person)
            .where(
                Person.patient_id == patient_id,
                Person.is_active == True,  # noqa: E712
            )
        )
        if name_hint:
            stmt = stmt.where(Person.name.ilike(f"%{name_hint}%"))

        stmt = stmt.order_by(Person.name.asc())
        result = await self._db.execute(stmt)
        persons = list(result.scalars().all())

        matched_person = persons[0] if persons else None
        exact_match = bool(matched_person)

        # Fallback: if name_hint was non-ASCII / Indic or not matched directly, load all family
        all_family = persons
        if not matched_person:
            all_stmt = (
                select(Person)
                .where(
                    Person.patient_id == patient_id,
                    Person.is_active == True,  # noqa: E712
                )
                .order_by(Person.name.asc())
            )
            all_res = await self._db.execute(all_stmt)
            all_family = list(all_res.scalars().all())

        related_memories: list[Memory] = []
        if matched_person:
            mem_stmt = (
                select(Memory)
                .join(Memory.people)
                .options(selectinload(Memory.people), selectinload(Memory.media))
                .where(
                    Memory.patient_id == patient_id,
                    Person.id == matched_person.id,
                )
                .order_by(Memory.event_date.desc())
                .limit(5)
            )
            mem_res = await self._db.execute(mem_stmt)
            related_memories = list(mem_res.scalars().all())

        return {
            "matched_person": matched_person,
            "all_known_people": all_family,
            "query_name": name_hint,
            "exact_match": exact_match,
            "related_memories": related_memories,
        }

    async def retrieve_patient_overview(self, patient_id: uuid.UUID) -> dict[str, Any]:
        """Fetches active family members, routine, and medications for conversational grounding."""
        # 1. Active family
        people_stmt = (
            select(Person)
            .where(Person.patient_id == patient_id, Person.is_active == True)
            .order_by(Person.name.asc())
            .limit(10)
        )
        people_res = await self._db.execute(people_stmt)
        people = list(people_res.scalars().all())

        # 2. Active medications
        meds_stmt = (
            select(Medication)
            .where(Medication.patient_id == patient_id, Medication.is_active == True)
            .order_by(Medication.name.asc())
            .limit(10)
        )
        meds_res = await self._db.execute(meds_stmt)
        meds = list(meds_res.scalars().all())

        # 3. Active routines
        routines_stmt = (
            select(Routine)
            .where(Routine.patient_id == patient_id, Routine.is_active == True)
            .order_by(Routine.scheduled_time.asc())
            .limit(5)
        )
        routines_res = await self._db.execute(routines_stmt)
        routines = list(routines_res.scalars().all())

        return {
            "all_known_people": people,
            "medications": meds,
            "routines": routines,
        }

    async def retrieve_visit_memories(
        self,
        patient_id: uuid.UUID,
        timeframe: str | None = None,
        target_name: str | None = None,
        reference_date: date | None = None,
        temporal: TemporalContext | None = None,
        direction: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieves visit-type memories and timeline events with strict date-filtering.
        Guarantees that queries like 'Who visited me yesterday?' ONLY retrieve yesterday's records.
        """
        today = reference_date or date.today()
        target_date: date | None = None
        if temporal and temporal.start_date:
            target_date = temporal.start_date
        elif timeframe == "yesterday":
            target_date = today - timedelta(days=1)
        elif timeframe == "today":
            target_date = today

        # 1. Query Memory table (VISIT and OUTING)
        stmt = (
            select(Memory)
            .options(selectinload(Memory.people), selectinload(Memory.media))
            .where(
                Memory.patient_id == patient_id,
                Memory.memory_type.in_([MemoryType.VISIT, MemoryType.OUTING]),
            )
        )
        if target_date:
            stmt = stmt.where(Memory.event_date == target_date)

        stmt = stmt.order_by(Memory.event_date.desc()).limit(10)
        result = await self._db.execute(stmt)
        memories = list(result.scalars().all())

        # 2. Query timeline Event table (VISIT and OUTING) with MATCHING DATE FILTER
        event_stmt = (
            select(Event)
            .where(
                Event.patient_id == patient_id,
                Event.event_type.in_([EventType.VISIT, EventType.OUTING]),
            )
        )
        if target_date:
            start_of_day = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc)
            end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=timezone.utc)
            event_stmt = event_stmt.where(
                Event.start_time >= start_of_day,
                Event.start_time <= end_of_day,
            )

        event_stmt = event_stmt.order_by(Event.start_time.desc()).limit(10)
        event_res = await self._db.execute(event_stmt)
        events = list(event_res.scalars().all())

        if target_name:
            target_lower = target_name.lower()
            memories = [
                m for m in memories
                if any(target_lower in p.name.lower() for p in m.people)
                or target_lower in m.title.lower()
                or (m.description and target_lower in m.description.lower())
                or (m.location and target_lower in m.location.lower())
            ]
            events = [
                ev for ev in events
                if target_lower in ev.title.lower()
                or (ev.description and target_lower in ev.description.lower())
                or (ev.location and target_lower in ev.location.lower())
            ]

        return {
            "memories": memories,
            "timeline_events": events,
            "timeframe": timeframe,
            "target_date": target_date,
            "target_name": target_name,
            "direction": direction,
            "has_records": bool(memories or events),
        }

    async def retrieve_daily_routine(
        self,
        patient_id: uuid.UUID,
        target_date: date | None = None,
        time_of_day: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieves recurring routines and scheduled timeline events for a given day and time slot.
        """
        target_d = target_date or date.today()
        day_bit = 1 << target_d.weekday()

        routine_stmt = select(Routine).where(
            Routine.patient_id == patient_id,
            Routine.is_active == True,  # noqa: E712
        )
        if time_of_day == "morning":
            routine_stmt = routine_stmt.where(
                Routine.category.in_([RoutineCategory.MORNING, RoutineCategory.MEAL, RoutineCategory.HYGIENE])
            )
        elif time_of_day == "afternoon":
            routine_stmt = routine_stmt.where(
                Routine.category.in_([RoutineCategory.AFTERNOON, RoutineCategory.MEAL, RoutineCategory.EXERCISE])
            )
        elif time_of_day == "evening":
            routine_stmt = routine_stmt.where(
                Routine.category.in_([RoutineCategory.EVENING, RoutineCategory.MEAL, RoutineCategory.SOCIAL])
            )

        routine_stmt = routine_stmt.order_by(Routine.scheduled_time.asc())
        routine_res = await self._db.execute(routine_stmt)
        all_routines = list(routine_res.scalars().all())
        active_routines = [r for r in all_routines if (r.days_of_week & day_bit) != 0]

        start_of_day = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=timezone.utc)
        end_of_day = datetime(target_d.year, target_d.month, target_d.day, 23, 59, 59, tzinfo=timezone.utc)

        events_stmt = (
            select(Event)
            .where(
                Event.patient_id == patient_id,
                Event.start_time >= start_of_day,
                Event.start_time <= end_of_day,
            )
        )
        if time_of_day == "morning":
            noon = datetime(target_d.year, target_d.month, target_d.day, 12, 0, 0, tzinfo=timezone.utc)
            events_stmt = events_stmt.where(Event.start_time < noon)
        elif time_of_day == "afternoon":
            noon = datetime(target_d.year, target_d.month, target_d.day, 12, 0, 0, tzinfo=timezone.utc)
            five_pm = datetime(target_d.year, target_d.month, target_d.day, 17, 0, 0, tzinfo=timezone.utc)
            events_stmt = events_stmt.where(Event.start_time >= noon, Event.start_time < five_pm)
        elif time_of_day == "evening":
            five_pm = datetime(target_d.year, target_d.month, target_d.day, 17, 0, 0, tzinfo=timezone.utc)
            events_stmt = events_stmt.where(Event.start_time >= five_pm)

        events_stmt = events_stmt.order_by(Event.start_time.asc())
        events_res = await self._db.execute(events_stmt)
        events = list(events_res.scalars().all())

        return {
            "routines": active_routines,
            "events": events,
            "target_date": target_d,
            "time_of_day": time_of_day,
            "has_records": bool(active_routines or events),
        }

    async def retrieve_medication_adherence(
        self,
        patient_id: uuid.UUID,
        target_date: date | None = None,
        timing_hint: str | None = None,
        med_name_hint: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieves active medications strictly matching the requested timing,
        along with adherence logs for the target date.
        If med_name_hint is provided, filters strictly for that specific medication.
        """
        target_d = target_date or date.today()

        med_stmt = select(Medication).where(
            Medication.patient_id == patient_id,
            Medication.is_active == True,  # noqa: E712
        )
        if med_name_hint:
            med_stmt = med_stmt.where(Medication.name.ilike(f"%{med_name_hint}%"))

        if timing_hint == "morning":
            med_stmt = med_stmt.where(
                Medication.timing.in_([MedicationTiming.BEFORE_BREAKFAST, MedicationTiming.AFTER_BREAKFAST])
            )
        elif timing_hint in ["evening", "night"]:
            med_stmt = med_stmt.where(
                Medication.timing.in_([
                    MedicationTiming.BEFORE_DINNER,
                    MedicationTiming.AFTER_DINNER,
                    MedicationTiming.BEDTIME,
                ])
            )
        elif timing_hint == "afternoon":
            med_stmt = med_stmt.where(
                Medication.timing.in_([MedicationTiming.BEFORE_LUNCH, MedicationTiming.AFTER_LUNCH])
            )

        med_stmt = med_stmt.order_by(Medication.name.asc())
        med_res = await self._db.execute(med_stmt)
        medications = list(med_res.scalars().all())

        adherence_logs: list[MedicationAdherenceLog] = []
        if medications:
            med_ids = [m.id for m in medications]
            log_stmt = select(MedicationAdherenceLog).where(
                MedicationAdherenceLog.medication_id.in_(med_ids),
                MedicationAdherenceLog.log_date == target_d,
            )
            log_res = await self._db.execute(log_stmt)
            adherence_logs = list(log_res.scalars().all())

        logs_by_med_id = {log.medication_id: log for log in adherence_logs}

        items = []
        all_taken = True if medications else False
        any_taken = False

        for med in medications:
            log = logs_by_med_id.get(med.id)
            is_taken = log.taken if log else False
            taken_at = log.taken_at if log else None
            if is_taken:
                any_taken = True
            else:
                all_taken = False
            items.append({
                "medication": med,
                "log": log,
                "is_taken": is_taken,
                "taken_at": taken_at,
            })

        return {
            "items": items,
            "medications": medications,
            "target_date": target_d,
            "timing_hint": timing_hint,
            "target_medication": med_name_hint,
            "has_medications": bool(medications),
            "all_taken": all_taken,
            "any_taken": any_taken,
            "has_logs": bool(adherence_logs),
        }

    # ── NEW: Medication Schedule Lookup (Active Prescription Catalogue) ───────
    async def retrieve_medication_schedule(
        self,
        patient_id: uuid.UUID,
        timing_hint: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieves active prescribed medications and their schedule times for the patient.
        Distinguished from adherence: answers 'What medicines do I take?' rather than 'Did I take it?'.
        """
        med_stmt = select(Medication).where(
            Medication.patient_id == patient_id,
            Medication.is_active == True,  # noqa: E712
        )
        if timing_hint == "morning":
            med_stmt = med_stmt.where(
                Medication.timing.in_([MedicationTiming.BEFORE_BREAKFAST, MedicationTiming.AFTER_BREAKFAST])
            )
        elif timing_hint in ["evening", "night"]:
            med_stmt = med_stmt.where(
                Medication.timing.in_([
                    MedicationTiming.BEFORE_DINNER,
                    MedicationTiming.AFTER_DINNER,
                    MedicationTiming.BEDTIME,
                ])
            )
        elif timing_hint == "afternoon":
            med_stmt = med_stmt.where(
                Medication.timing.in_([MedicationTiming.BEFORE_LUNCH, MedicationTiming.AFTER_LUNCH])
            )

        med_stmt = med_stmt.order_by(Medication.scheduled_time.asc().nulls_last(), Medication.name.asc())
        med_res = await self._db.execute(med_stmt)
        medications = list(med_res.scalars().all())

        return {
            "medications": medications,
            "timing_hint": timing_hint,
            "has_medications": bool(medications),
        }

    # ── NEW: Cognitive Game Performance Retrieval ─────────────────────────────
    async def retrieve_game_progress(
        self,
        patient_id: uuid.UUID,
        temporal: TemporalContext | None = None,
        game_name: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        """
        Retrieves cognitive game play sessions strictly for the patient,
        applying temporal date bounds (e.g. today, yesterday) and game filters.
        """
        stmt = (
            select(GameSession)
            .options(selectinload(GameSession.game))
            .where(GameSession.patient_id == patient_id)
        )

        # Enforce temporal filtering if bounded
        if temporal and temporal.is_bounded:
            if temporal.start_date:
                s_dt = datetime.combine(temporal.start_date, time.min, tzinfo=timezone.utc)
                stmt = stmt.where(GameSession.started_at >= s_dt)
            if temporal.end_date:
                e_dt = datetime.combine(temporal.end_date, time.max, tzinfo=timezone.utc)
                stmt = stmt.where(GameSession.started_at <= e_dt)

        if game_name:
            stmt = stmt.join(GameSession.game).where(Game.name.ilike(f"%{game_name}%"))

        stmt = stmt.order_by(GameSession.started_at.desc()).limit(limit)
        res = await self._db.execute(stmt)
        sessions = list(res.scalars().all())

        # Compute aggregate performance indicators for prompt context
        avg_acc = None
        avg_rt = None
        if sessions:
            acc_vals = [s.accuracy for s in sessions if s.accuracy is not None]
            if acc_vals:
                avg_acc = round(sum(acc_vals) / len(acc_vals), 2)
            rt_vals = [s.reaction_time_ms for s in sessions if s.reaction_time_ms is not None]
            if rt_vals:
                avg_rt = int(sum(rt_vals) / len(rt_vals))

        return {
            "sessions": sessions,
            "has_sessions": bool(sessions),
            "session_count": len(sessions),
            "avg_accuracy": avg_acc,
            "avg_reaction_time_ms": avg_rt,
            "temporal": temporal,
            "game_name": game_name,
        }

    # ── NEW: Cognitive Metrics & CPI Progress Retrieval ───────────────────────
    async def retrieve_cognitive_progress(
        self,
        patient_id: uuid.UUID,
        temporal: TemporalContext | None = None,
        limit: int = 7,
    ) -> dict[str, Any]:
        """
        Retrieves daily performance statistics and Cognitive Performance Index (CPI) metrics.
        Calculates trend direction while framing CPI strictly as an assistive indicator.
        """
        daily_stmt = select(DailyStatistic).where(DailyStatistic.patient_id == patient_id)
        metric_stmt = select(CognitiveMetric).where(CognitiveMetric.patient_id == patient_id)

        if temporal and temporal.is_bounded:
            if temporal.start_date:
                daily_stmt = daily_stmt.where(DailyStatistic.stat_date >= temporal.start_date)
                metric_stmt = metric_stmt.where(CognitiveMetric.metric_date >= temporal.start_date)
            if temporal.end_date:
                daily_stmt = daily_stmt.where(DailyStatistic.stat_date <= temporal.end_date)
                metric_stmt = metric_stmt.where(CognitiveMetric.metric_date <= temporal.end_date)

        daily_stmt = daily_stmt.order_by(DailyStatistic.stat_date.desc()).limit(limit)
        metric_stmt = metric_stmt.order_by(CognitiveMetric.metric_date.desc()).limit(limit)

        daily_res = await self._db.execute(daily_stmt)
        metric_res = await self._db.execute(metric_stmt)

        daily_stats = list(daily_res.scalars().all())
        cognitive_metrics = list(metric_res.scalars().all())

        latest_metric = cognitive_metrics[0] if cognitive_metrics else None
        latest_cpi = latest_metric.cpi_score if latest_metric else None
        cpi_delta = latest_metric.cpi_delta if latest_metric else None

        trend = "stable"
        if cpi_delta is not None:
            if cpi_delta > 1.0:
                trend = "improving"
            elif cpi_delta < -1.0:
                trend = "declining"

        return {
            "daily_stats": daily_stats,
            "cognitive_metrics": cognitive_metrics,
            "latest_cpi": latest_cpi,
            "cpi_delta": cpi_delta,
            "cpi_trend": trend,
            "has_data": bool(daily_stats or cognitive_metrics),
            "temporal": temporal,
        }

    # ── NEW: Timeline Event / Calendar Lookup ─────────────────────────────────
    async def retrieve_events(
        self,
        patient_id: uuid.UUID,
        temporal: TemporalContext | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        """
        Retrieves scheduled appointments, outings, and calendar events for the patient.
        If temporal context is unbounded, queries upcoming events from now forward.
        """
        stmt = select(Event).where(Event.patient_id == patient_id)

        if temporal and temporal.is_bounded:
            if temporal.start_date:
                s_dt = datetime.combine(temporal.start_date, time.min, tzinfo=timezone.utc)
                stmt = stmt.where(Event.start_time >= s_dt)
            if temporal.end_date:
                e_dt = datetime.combine(temporal.end_date, time.max, tzinfo=timezone.utc)
                stmt = stmt.where(Event.start_time <= e_dt)
        else:
            # Default to upcoming events
            stmt = stmt.where(Event.start_time >= datetime.now(timezone.utc))

        stmt = stmt.order_by(Event.start_time.asc()).limit(limit)
        res = await self._db.execute(stmt)
        events = list(res.scalars().all())

        return {
            "events": events,
            "has_events": bool(events),
            "temporal": temporal,
        }

    # ── NEW: Broad Temporal Recall (Cross-Domain Daily Recap) ─────────────────
    async def retrieve_temporal_recall(
        self,
        patient_id: uuid.UUID,
        target_date: date | None = None,
        temporal: TemporalContext | None = None,
    ) -> dict[str, Any]:
        """
        Retrieves grounded activity records across all domains (memories, visits,
        events, game sessions, medication logs) for a specific target date (e.g. yesterday).
        Powers broad temporal queries like 'What happened yesterday?'.
        """
        target_d = target_date or (temporal.start_date if temporal else None) or (date.today() - timedelta(days=1))

        # 1. Memories on target date
        mem_stmt = (
            select(Memory)
            .options(selectinload(Memory.people), selectinload(Memory.media))
            .where(
                Memory.patient_id == patient_id,
                Memory.event_date == target_d,
            )
            .order_by(Memory.created_at.desc())
        )
        mem_res = await self._db.execute(mem_stmt)
        memories = list(mem_res.scalars().all())

        # 2. Timeline Events on target date
        start_of_day = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=timezone.utc)
        end_of_day = datetime(target_d.year, target_d.month, target_d.day, 23, 59, 59, tzinfo=timezone.utc)
        ev_stmt = (
            select(Event)
            .where(
                Event.patient_id == patient_id,
                Event.start_time >= start_of_day,
                Event.start_time <= end_of_day,
            )
            .order_by(Event.start_time.asc())
        )
        ev_res = await self._db.execute(ev_stmt)
        events = list(ev_res.scalars().all())

        # 3. Game sessions on target date
        g_stmt = (
            select(GameSession)
            .options(selectinload(GameSession.game))
            .where(
                GameSession.patient_id == patient_id,
                GameSession.started_at >= start_of_day,
                GameSession.started_at <= end_of_day,
            )
            .order_by(GameSession.started_at.desc())
        )
        g_res = await self._db.execute(g_stmt)
        sessions = list(g_res.scalars().all())

        # 4. Medication adherence logs on target date
        med_stmt = (
            select(MedicationAdherenceLog)
            .options(selectinload(MedicationAdherenceLog.medication))
            .join(Medication, MedicationAdherenceLog.medication_id == Medication.id)
            .where(
                Medication.patient_id == patient_id,
                MedicationAdherenceLog.log_date == target_d,
            )
        )
        med_res = await self._db.execute(med_stmt)
        med_logs = list(med_res.scalars().all())

        has_data = bool(memories or events or sessions or med_logs)

        return {
            "target_date": target_d,
            "memories": memories,
            "events": events,
            "game_sessions": sessions,
            "medication_logs": med_logs,
            "has_data": has_data,
            "temporal": temporal,
        }

