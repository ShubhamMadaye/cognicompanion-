"""
CogniCompanion — Games Domain Schemas
========================================
Pydantic v2 schemas for Game definitions and GameSession logs.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.domains.games.models import DifficultyLevel, GameType, SessionStatus


# ── Game Schemas ──────────────────────────────────────────────────────────────

class GameResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    game_type: GameType
    name: str
    description: str | None
    instructions: str | None
    min_difficulty: DifficultyLevel
    max_difficulty: DifficultyLevel
    estimated_duration_seconds: int
    icon_emoji: str | None


# ── Game Session Schemas ──────────────────────────────────────────────────────

class CreateGameSessionRequest(BaseModel):
    game_type: GameType
    difficulty_level: DifficultyLevel = DifficultyLevel.MEDIUM
    score: int = Field(ge=0, default=0)
    accuracy: float = Field(ge=0.0, le=1.0, default=1.0)
    reaction_time_ms: int | None = Field(default=None, ge=0)
    mistakes: int = Field(ge=0, default=0)
    total_items: int = Field(ge=1, default=1)
    correct_items: int = Field(ge=0, default=1)
    duration_seconds: int | None = Field(default=None, ge=0)


class GameCardItem(BaseModel):
    id: str
    pair_id: str
    label: str
    image_url: str | None = None
    emoji: str | None = None


class GameQuestionItem(BaseModel):
    question_text: str
    image_url: str | None = None
    options: list[str]
    correct_option: str
    memory_id: str | None = None


class GameContentResponse(BaseModel):
    game_type: GameType
    difficulty_level: DifficultyLevel
    is_personalized: bool
    instructions: str
    cards: list[GameCardItem] | None = None
    sequence: list[str] | None = None
    questions: list[GameQuestionItem] | None = None
    target_objects: list[str] | None = None
    candidate_objects: list[str] | None = None
    disclaimer: str = "CogniCompanion activities are designed for assistive cognitive stimulation based on observed engagement, not clinical medical diagnosis."


class GenerateGameContentRequest(BaseModel):
    difficulty_level: DifficultyLevel | None = None
    personalize: bool = True


class GameSessionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    patient_id: uuid.UUID
    game_id: uuid.UUID
    game_type: GameType | None = None
    status: SessionStatus
    difficulty_level: DifficultyLevel
    score: int | None
    accuracy: float | None
    reaction_time_ms: int | None
    mistakes: int | None
    total_items: int | None
    correct_items: int | None
    next_difficulty: DifficultyLevel | None
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
