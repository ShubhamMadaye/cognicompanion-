"""
CogniCompanion — Analytics Router
==================================
Endpoints for Cognitive Performance Index (CPI), component explainability,
and daily activity analytics.

All endpoints strictly verify patient-caregiver authorization.
CPI is presented as an assistive performance indicator, NOT a medical diagnosis.
"""

import uuid
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import (
    verify_patient_self_or_caregiver_access,
)
from app.domains.analytics.schemas import (
    CPIMetricsResponse,
    CPITrendResponse,
    DailySummaryResponse,
)
from app.domains.analytics.service import AnalyticsService

router = APIRouter(prefix="/patients/{patient_id}/analytics", tags=["Analytics & CPI"])


@router.get(
    "/cpi",
    response_model=CPIMetricsResponse,
    summary="Get patient Cognitive Performance Index (CPI) and explainable breakdown",
)
async def get_patient_cpi(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    metric_date: Optional[date] = Query(
        None, description="Date to evaluate CPI for (defaults to today)"
    ),
) -> CPIMetricsResponse:
    """
    Returns the Cognitive Performance Index (0–100) and its four weighted components:
      - memory_accuracy (40%)
      - reaction_performance (25%)
      - completion_rate (20%)
      - engagement_score (15%)

    If the patient does not have enough recorded activity, returns status=INSUFFICIENT_DATA
    with cpi_score=None instead of manufacturing a misleading score.

    *Note: This is an assistive performance indicator based on app activity. It is not a medical diagnosis.*
    """
    service = AnalyticsService(db)
    return await service.get_cpi_response(patient_id, metric_date)


@router.get(
    "/cpi/trends",
    response_model=CPITrendResponse,
    summary="Get historical CPI trends for charts and sparklines",
)
async def get_patient_cpi_trends(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(7, ge=1, le=90, description="Number of past days to return"),
) -> CPITrendResponse:
    """
    Returns daily historical CPI scores and individual component values over the specified time range.
    """
    service = AnalyticsService(db)
    return await service.get_cpi_trends(patient_id, days)


@router.get(
    "/daily",
    response_model=DailySummaryResponse,
    summary="Get daily summary of games, medications, routines, and interactions",
)
async def get_patient_daily_summary(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    stat_date: Optional[date] = Query(
        None, description="Date for daily summary (defaults to today)"
    ),
) -> DailySummaryResponse:
    """
    Returns aggregated daily snapshot metrics for games, medication adherence,
    routine completion, and voice assistant interactions.
    """
    service = AnalyticsService(db)
    return await service.get_daily_summary(patient_id, stat_date)


@router.post(
    "/recalculate",
    response_model=CPIMetricsResponse,
    summary="Recalculate daily statistics and CPI on-demand",
)
async def recalculate_patient_cpi(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    target_date: Optional[date] = Query(
        None, description="Date to recalculate (defaults to today)"
    ),
) -> CPIMetricsResponse:
    """
    Forces on-demand re-aggregation of raw game sessions, adherence logs,
    and assistant turns, updating both DailyStatistic and CognitiveMetric.
    """
    service = AnalyticsService(db)
    return await service.get_cpi_response(patient_id, target_date)
