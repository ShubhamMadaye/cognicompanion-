"""
CogniCompanion — Auth Router
===============================
Endpoints:
  POST /auth/register → register account
  POST /auth/login    → authenticate, get tokens
  POST /auth/refresh  → get new access token
  GET  /auth/me       → current user info
  POST /auth/logout   → session token invalidation
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_user
from app.domains.auth.schemas import (
    AccessTokenResponse,
    LoginRequest,
    LogoutResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.domains.auth.service import AuthService
from app.domains.patients.models import User
from app.domains.patients.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201, summary="Register a new user account")
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Register a new user account (Caregiver, Doctor, or Patient).
    Automatically provisions a profile if role=PATIENT.
    Returns access and refresh tokens along with user information.
    """
    service = AuthService(db)
    access_token, refresh_token, user = await service.register(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        role=body.role,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse, summary="Authenticate and receive tokens")
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Authenticate with email + password.

    Returns:
        access_token  — short-lived JWT (30 min), use in Authorization: Bearer header.
        refresh_token — long-lived JWT (7 days), use to get new access tokens.
        user          — current user profile.
    """
    service = AuthService(db)
    access_token, refresh_token, user = await service.login(body.email, body.password)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=AccessTokenResponse, summary="Refresh access token")
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccessTokenResponse:
    """
    Exchange a valid refresh token for a new access token.
    The refresh token is NOT rotated — it remains valid until it expires.
    """
    service = AuthService(db)
    access_token = await service.refresh_access_token(body.refresh_token)
    return AccessTokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse, summary="Get current user info")
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Return the authenticated user's profile information."""
    return UserResponse.model_validate(current_user)


@router.post("/logout", response_model=LogoutResponse, summary="Log out and invalidate user tokens")
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LogoutResponse:
    """
    Invalidate current user session tokens by incrementing token_version.
    All tokens issued prior to this call will be rejected.
    """
    service = AuthService(db)
    await service.logout(current_user)
    return LogoutResponse(message="Successfully logged out.")
