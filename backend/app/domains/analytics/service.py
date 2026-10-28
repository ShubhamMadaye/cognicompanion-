"""
CogniCompanion — Analytics & CPI Service
=========================================
Aggregates activity data and computes the Cognitive Performance Index (CPI).

Key Design Principles:
  1. Assistive Performance Indicator — NOT a medical diagnosis.
  2. Insufficient Data Guard — brand new patients with no activity return INSUFFICIENT_DATA.
  3. Explicit Formula:
       CPI = (0.40 * memory + 0.25 * reaction + 0.20 * completion + 0.15 * engagement) * 100
  4. Bounded Normalization:
       - Memory accuracy: [0.0, 1.0] from completed games.
       - Reaction time: [500ms, 4000ms] clamped and inverted to [0.0, 1.0].
       - Completion rate: [0.0, 1.0] from med and routine adherence.
       - Engagement score: [0.0, 1.0] bounded sum of games and voice assistant turns.
"""

import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import and_, cast, Date, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analytics.models import CognitiveMetric, DailyStatistic
from app.domains.analytics.schemas import (
    CPIMetricsResponse,
    CPIStatus,
    CPITrendItem,
    CPITrendResponse,
    DailySummaryResponse,
)
from app.domains.games.models import DifficultyLevel, GameSession, SessionStatus
from app.domains.timeline.models import (
    Medication,
    MedicationAdherenceLog,
    Routine,
)
from app.domains.voice.models import Conversation, ConversationMessage

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def aggregate_daily_statistics(
        self, patient_id: uuid.UUID, target_date: date
    ) -> DailyStatistic:
        """
        Aggregates raw activity logs into a DailyStatistic record for (patient_id, target_date).
        Updates existing record or creates a new one.
        """
        # Determine datetime boundaries for cross-dialect compatibility (PostgreSQL & SQLite)
        start_of_day = datetime.combine(target_date, time.min)
        end_of_day = datetime.combine(target_date, time.max)

        # 1. Game sessions on target_date
        game_stmt = select(GameSession).where(
            GameSession.patient_id == patient_id,
            GameSession.started_at >= start_of_day,
            GameSession.started_at <= end_of_day,
        )
        game_res = await self.db.execute(game_stmt)
        sessions = game_res.scalars().all()

        completed_sessions = [s for s in sessions if s.status == SessionStatus.COMPLETED]
        games_total = len(sessions)
        games_completed = len(completed_sessions)

        valid_accuracies = [s.accuracy for s in completed_sessions if s.accuracy is not None]
        avg_accuracy = (
            round(sum(valid_accuracies) / len(valid_accuracies), 4)
            if valid_accuracies
            else None
        )

        valid_reactions = [s.reaction_time_ms for s in completed_sessions if s.reaction_time_ms is not None]
        avg_reaction_ms = (
            int(sum(valid_reactions) / len(valid_reactions))
            if valid_reactions
            else None
        )

        # 2. Medication adherence on target_date
        active_meds_stmt = select(func.count(Medication.id)).where(
            Medication.patient_id == patient_id,
            Medication.is_active == True,
        )
        meds_sched_res = await self.db.execute(active_meds_stmt)
        medications_scheduled = meds_sched_res.scalar() or 0

        # Adherence logs for this date
        adherence_stmt = select(MedicationAdherenceLog).join(
            Medication, MedicationAdherenceLog.medication_id == Medication.id
        ).where(
            Medication.patient_id == patient_id,
            MedicationAdherenceLog.log_date == target_date,
        )
        adh_res = await self.db.execute(adherence_stmt)
        adh_logs = adh_res.scalars().all()
        medications_taken = sum(1 for log in adh_logs if log.taken)

        medication_adherence = (
            round(medications_taken / medications_scheduled, 4)
            if medications_scheduled > 0
            else 1.0 if medications_taken > 0 else None
        )

        # 3. Routine adherence on target_date
        active_routines_stmt = select(func.count(Routine.id)).where(
            Routine.patient_id == patient_id,
            Routine.is_active == True,
        )
        routines_sched_res = await self.db.execute(active_routines_stmt)
        routines_scheduled = routines_sched_res.scalar() or 0
        # By default for MVP, routines confirmed if patient was active
        routines_completed = min(routines_scheduled, medications_taken) if routines_scheduled > 0 else 0
        routine_adherence = (
            round(routines_completed / routines_scheduled, 4)
            if routines_scheduled > 0
            else 1.0
        )

        # 4. Assistant interactions on target_date
        interactions_stmt = select(func.count(ConversationMessage.id)).join(
            Conversation, ConversationMessage.conversation_id == Conversation.id
        ).where(
            Conversation.patient_id == patient_id,
            ConversationMessage.created_at >= start_of_day,
            ConversationMessage.created_at <= end_of_day,
            ConversationMessage.role == "patient",
        )
        inter_res = await self.db.execute(interactions_stmt)
        assistant_interactions = inter_res.scalar() or 0

        # Check existing DailyStatistic
        stat_stmt = select(DailyStatistic).where(
            DailyStatistic.patient_id == patient_id,
            DailyStatistic.stat_date == target_date,
        )
        stat_res = await self.db.execute(stat_stmt)
        stat = stat_res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if not stat:
            stat = DailyStatistic(
                id=uuid.uuid4(),
                patient_id=patient_id,
                stat_date=target_date,
                games_completed=games_completed,
                games_total=games_total,
                average_game_accuracy=avg_accuracy,
                average_reaction_time_ms=avg_reaction_ms,
                medications_scheduled=medications_scheduled,
                medications_taken=medications_taken,
                medication_adherence=medication_adherence,
                routines_scheduled=routines_scheduled,
                routines_completed=routines_completed,
                routine_adherence=routine_adherence,
                assistant_interactions_count=assistant_interactions,
                computed_at=now,
            )
            self.db.add(stat)
        else:
            stat.games_completed = games_completed
            stat.games_total = games_total
            stat.average_game_accuracy = avg_accuracy
            stat.average_reaction_time_ms = avg_reaction_ms
            stat.medications_scheduled = medications_scheduled
            stat.medications_taken = medications_taken
            stat.medication_adherence = medication_adherence
            stat.routines_scheduled = routines_scheduled
            stat.routines_completed = routines_completed
            stat.routine_adherence = routine_adherence
            stat.assistant_interactions_count = assistant_interactions
            stat.computed_at = now

        await self.db.flush()
        return stat

    async def compute_cpi_metric(
        self, patient_id: uuid.UUID, target_date: date
    ) -> tuple[CognitiveMetric, CPIStatus, Optional[str]]:
        """
        Computes the Cognitive Performance Index using the verified explicit formula:
          weighted_score = (0.40 * mem + 0.25 * react + 0.20 * comp + 0.15 * eng)
          cpi = clamp(weighted_score * 100, 0.0, 100.0)

        Handles Insufficient Data when patient activity is below baseline.
        """
        stat = await self.aggregate_daily_statistics(patient_id, target_date)

        # Baseline check: If 0 games and fewer than 2 total recorded interactions
        total_activity_events = (
            stat.games_completed
            + stat.medications_taken
            + stat.assistant_interactions_count
        )

        if stat.games_completed == 0 and total_activity_events < 2:
            # Insufficient Data condition
            status = CPIStatus.INSUFFICIENT_DATA
            message = "Not enough activity yet. Complete a few activities to establish a baseline."
            cpi_score = None
            memory_accuracy = None
            reaction_performance = None
            completion_rate = None
            engagement_score = None
        else:
            status = CPIStatus.SUFFICIENT_DATA
            message = None

            # 1. Memory Accuracy (0.0 to 1.0)
            memory_accuracy = stat.average_game_accuracy

            # 2. Reaction Performance: Bounded normalization [500ms, 4000ms]
            if stat.average_reaction_time_ms is not None and stat.average_reaction_time_ms > 0:
                # 500ms or faster -> 1.0; 4000ms or slower -> 0.0
                raw_react = 1.0 - ((stat.average_reaction_time_ms - 500.0) / 3500.0)
                reaction_performance = round(max(0.0, min(1.0, raw_react)), 4)
            else:
                reaction_performance = None

            # 3. Completion Rate: Medication + Routine Adherence
            total_scheduled = stat.medications_scheduled + stat.routines_scheduled
            total_completed = stat.medications_taken + stat.routines_completed
            if total_scheduled > 0:
                completion_rate = round(min(1.0, total_completed / total_scheduled), 4)
            elif total_completed > 0:
                completion_rate = 1.0
            else:
                completion_rate = None

            # 4. Engagement Score: Bounded normalized metric
            raw_eng = (stat.games_completed * 0.25) + (stat.assistant_interactions_count * 0.15)
            engagement_score = round(max(0.0, min(1.0, raw_eng)), 4)

            # 5. Weighted Formula with dynamic normalization for missing components
            weights: list[tuple[float, float]] = []
            if memory_accuracy is not None:
                weights.append((0.40, memory_accuracy))
            if reaction_performance is not None:
                weights.append((0.25, reaction_performance))
            if completion_rate is not None:
                weights.append((0.20, completion_rate))
            if engagement_score is not None:
                weights.append((0.15, engagement_score))

            if weights:
                total_w = sum(w for w, _ in weights)
                weighted_sum = sum(w * val for w, val in weights) / total_w
                cpi_score = round(max(0.0, min(100.0, weighted_sum * 100.0)), 1)
            else:
                cpi_score = None
                status = CPIStatus.INSUFFICIENT_DATA
                message = "Not enough activity yet. Complete a few activities to establish a baseline."

        # Fetch previous valid CPI to compute delta
        prev_stmt = (
            select(CognitiveMetric)
            .where(
                CognitiveMetric.patient_id == patient_id,
                CognitiveMetric.metric_date < target_date,
                CognitiveMetric.cpi_score.isnot(None),
            )
            .order_by(desc(CognitiveMetric.metric_date))
            .limit(1)
        )
        prev_res = await self.db.execute(prev_stmt)
        prev_metric = prev_res.scalar_one_or_none()

        cpi_delta = None
        if cpi_score is not None and prev_metric and prev_metric.cpi_score is not None:
            cpi_delta = round(cpi_score - prev_metric.cpi_score, 1)

        # Update DailyStatistic's CPI
        stat.cpi_score = cpi_score

        # Check existing CognitiveMetric for target_date
        metric_stmt = select(CognitiveMetric).where(
            CognitiveMetric.patient_id == patient_id,
            CognitiveMetric.metric_date == target_date,
        )
        metric_res = await self.db.execute(metric_stmt)
        metric = metric_res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if not metric:
            metric = CognitiveMetric(
                id=uuid.uuid4(),
                patient_id=patient_id,
                metric_date=target_date,
                memory_accuracy=memory_accuracy,
                reaction_performance=reaction_performance,
                completion_rate=completion_rate,
                engagement_score=engagement_score,
                cpi_score=cpi_score,
                cpi_delta=cpi_delta,
                notes=message,
                computed_at=now,
            )
            self.db.add(metric)
        else:
            metric.memory_accuracy = memory_accuracy
            metric.reaction_performance = reaction_performance
            metric.completion_rate = completion_rate
            metric.engagement_score = engagement_score
            metric.cpi_score = cpi_score
            metric.cpi_delta = cpi_delta
            metric.notes = message
            metric.computed_at = now

        await self.db.commit()
        await self.db.refresh(metric)
        await self.db.refresh(stat)

        return metric, status, message

    async def get_cpi_response(
        self, patient_id: uuid.UUID, target_date: Optional[date] = None
    ) -> CPIMetricsResponse:
        """Returns the full explainable CPI breakdown for the caregiver dashboard."""
        eval_date = target_date or date.today()
        metric, status, message = await self.compute_cpi_metric(patient_id, eval_date)

        # Fetch the daily statistics for sample counts
        stat_stmt = select(DailyStatistic).where(
            DailyStatistic.patient_id == patient_id,
            DailyStatistic.stat_date == eval_date,
        )
        stat_res = await self.db.execute(stat_stmt)
        stat = stat_res.scalar_one_or_none()

        return CPIMetricsResponse(
            patient_id=patient_id,
            metric_date=eval_date,
            status=status,
            cpi_score=metric.cpi_score,
            cpi_delta=metric.cpi_delta,
            memory_accuracy=metric.memory_accuracy,
            reaction_performance=metric.reaction_performance,
            completion_rate=metric.completion_rate,
            engagement_score=metric.engagement_score,
            games_completed=stat.games_completed if stat else 0,
            games_total=stat.games_total if stat else 0,
            medications_scheduled=stat.medications_scheduled if stat else 0,
            medications_taken=stat.medications_taken if stat else 0,
            routines_scheduled=stat.routines_scheduled if stat else 0,
            routines_completed=stat.routines_completed if stat else 0,
            assistant_interactions=stat.assistant_interactions_count if stat else 0,
            message=message,
        )

    async def get_cpi_trends(
        self, patient_id: uuid.UUID, days: int = 7
    ) -> CPITrendResponse:
        """Returns historical trend of CPI and component scores for charts."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        stmt = (
            select(CognitiveMetric)
            .where(
                CognitiveMetric.patient_id == patient_id,
                CognitiveMetric.metric_date >= start_date,
                CognitiveMetric.metric_date <= end_date,
            )
            .order_by(CognitiveMetric.metric_date.asc())
        )
        res = await self.db.execute(stmt)
        metrics_by_date = {m.metric_date: m for m in res.scalars().all()}

        items: list[CPITrendItem] = []
        cur = start_date
        while cur <= end_date:
            m = metrics_by_date.get(cur)
            items.append(
                CPITrendItem(
                    date=cur,
                    cpi_score=m.cpi_score if m else None,
                    memory_accuracy=m.memory_accuracy if m else None,
                    reaction_performance=m.reaction_performance if m else None,
                    completion_rate=m.completion_rate if m else None,
                    engagement_score=m.engagement_score if m else None,
                )
            )
            cur += timedelta(days=1)

        return CPITrendResponse(patient_id=patient_id, days=days, trends=items)

    async def get_daily_summary(
        self, patient_id: uuid.UUID, target_date: Optional[date] = None
    ) -> DailySummaryResponse:
        """Returns today's aggregated activity summary."""
        eval_date = target_date or date.today()
        stat = await self.aggregate_daily_statistics(patient_id, eval_date)
        return DailySummaryResponse.model_validate(stat)
