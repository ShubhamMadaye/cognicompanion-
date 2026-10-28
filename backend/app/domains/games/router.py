"""
CogniCompanion — Games Domain Router
=======================================
API Endpoints for Game catalogue and Patient Game Sessions.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import verify_patient_self_or_caregiver_access
from app.domains.games.models import DifficultyLevel, GameType
from app.domains.games.schemas import (
    CreateGameSessionRequest,
    GameContentResponse,
    GameResponse,
    GameSessionResponse,
)
from app.domains.games.service import GamesService

router = APIRouter(tags=["Games"])


@router.get(
    "/games",
    response_model=list[GameResponse],
    summary="Get available cognitive game catalog",
)
async def list_games(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[GameResponse]:
    service = GamesService(db)
    games = await service.list_games()
    return [GameResponse.model_validate(g) for g in games]


@router.post(
    "/patients/{patient_id}/games/{game_type}/generate",
    response_model=GameContentResponse,
    summary="Generate personalized cognitive activity content",
)
async def generate_game_content(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    game_type: GameType,
    db: Annotated[AsyncSession, Depends(get_db)],
    difficulty: DifficultyLevel = Query(default=DifficultyLevel.MEDIUM),
    personalize: bool = Query(default=True),
) -> GameContentResponse:
    """
    Generates tailored cognitive stimulation activity content.
    Seamlessly incorporates patient's actual memories and people when available.
    """
    service = GamesService(db)
    return await service.generate_game_content(
        patient_id=patient_id,
        game_type=game_type,
        difficulty=difficulty,
        personalize=personalize,
    )


@router.post(
    "/patients/{patient_id}/games/sessions",
    response_model=GameSessionResponse,
    status_code=201,
    summary="Submit completed game session results",
)
async def record_game_session(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    body: CreateGameSessionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GameSessionResponse:
    """
    Submits a completed game session from the mobile app.
    Automatically evaluates adaptive difficulty and triggers CPI score recalculation.
    """
    service = GamesService(db)
    session = await service.record_session(patient_id, body)
    
    # Construct response with game_type
    resp = GameSessionResponse.model_validate(session)
    resp.game_type = body.game_type
    return resp


@router.get(
    "/patients/{patient_id}/games/sessions",
    response_model=list[GameSessionResponse],
    summary="Get patient game history",
)
async def list_game_sessions(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, le=100),
) -> list[GameSessionResponse]:
    service = GamesService(db)
    sessions = await service.list_patient_sessions(patient_id, limit=limit)
    
    results = []
    for s in sessions:
        item = GameSessionResponse.model_validate(s)
        if s.game:
            item.game_type = s.game.game_type
        results.append(item)
    return results
