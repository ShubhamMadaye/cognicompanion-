"""
CogniCompanion — Analytics Domain Schemas
==========================================
Pydantic schemas for Cognitive Performance Index (CPI)
and daily activity analytics.
"""

import enum
import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

CPI_NON_MEDICAL_DISCLAIMER = (
    "This is an assistive performance indicator based on app activity. "
    "It is not a medical diagnosis."
)


class CPIStatus(str, enum.Enum):
    SUFFICIENT_DATA = "SUFFICIENT_DATA"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class CPIMetricsResponse(BaseModel):
    """
    Explainable breakdown of the Cognitive Performance Index.
    All components normalized 0.0–1.0, CPI scaled 0–100.
    """
    patient_id: uuid.UUID
    metric_date: date
    status: CPIStatus = CPIStatus.SUFFICIENT_DATA
    cpi_score: Optional[float] = Field(
        None, description="Overall CPI (0–100), or None if insufficient baseline data"
    )
    cpi_delta: Optional[float] = Field(
        None, description="Change in CPI vs previous valid measurement"
    )

    # Component Scores (0.0 to 1.0)
    memory_accuracy: Optional[float] = Field(
        None, description="Average accuracy across completed games (40% weight)"
    )
    reaction_performance: Optional[float] = Field(
        None, description="Normalized reaction speed: faster is closer to 1.0 (25% weight)"
    )
    completion_rate: Optional[float] = Field(
        None, description="Adherence across scheduled meds & routines (20% weight)"
    )
    engagement_score: Optional[float] = Field(
        None, description="Activity & assistant interaction level (15% weight)"
    )

    # Explainability & Sample Counts
    games_completed: int = 0
    games_total: int = 0
    medications_scheduled: int = 0
    medications_taken: int = 0
    routines_scheduled: int = 0
    routines_completed: int = 0
    assistant_interactions: int = 0

    # Non-Medical Disclaimer
    disclaimer: str = CPI_NON_MEDICAL_DISCLAIMER
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CPITrendItem(BaseModel):
    date: date
    cpi_score: Optional[float] = None
    memory_accuracy: Optional[float] = None
    reaction_performance: Optional[float] = None
    completion_rate: Optional[float] = None
    engagement_score: Optional[float] = None


class CPITrendResponse(BaseModel):
    patient_id: uuid.UUID
    days: int
    trends: list[CPITrendItem]
    disclaimer: str = CPI_NON_MEDICAL_DISCLAIMER


class DailySummaryResponse(BaseModel):
    patient_id: uuid.UUID
    stat_date: date
    games_completed: int
    games_total: int
    average_game_accuracy: Optional[float] = None
    average_reaction_time_ms: Optional[int] = None
    medications_scheduled: int
    medications_taken: int
    medication_adherence: Optional[float] = None
    routines_scheduled: int
    routines_completed: int
    routine_adherence: Optional[float] = None
    assistant_interactions_count: int
    cpi_score: Optional[float] = None
    disclaimer: str = CPI_NON_MEDICAL_DISCLAIMER

    model_config = ConfigDict(from_attributes=True)
