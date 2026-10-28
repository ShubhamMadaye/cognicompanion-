"""
CogniCompanion — Auth Domain Service
=======================================
Business logic for authentication: login, registration, token refresh, logout.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.domains.patients.models import Patient, PreferredLanguage, User, UserRole


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.CAREGIVER,
    ) -> tuple[str, str, User]:
        """
        Register a new user, automatically create a patient profile if role=PATIENT,
        and return (access_token, refresh_token, user).
        """
        result = await self._db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ConflictError("A user with this email address already exists.")

        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hash_password(password),
            role=role,
            full_name=full_name,
            is_active=True,
            token_version=0,
        )
        self._db.add(user)
        await self._db.flush()

        if role == UserRole.PATIENT:
            patient = Patient(
                id=uuid.uuid4(),
                user_id=user.id,
                preferred_language=PreferredLanguage.ENGLISH,
            )
            self._db.add(patient)
            await self._db.flush()

        await self._db.commit()
        await self._db.refresh(user)

        access_token = create_access_token(
            user_id=str(user.id),
            role=user.role.value,
            token_version=user.token_version,
        )
        refresh_token = create_refresh_token(
            user_id=str(user.id),
            token_version=user.token_version,
        )
        return access_token, refresh_token, user

    async def login(self, email: str, password: str) -> tuple[str, str, User]:
        """
        Authenticate user credentials and return (access_token, refresh_token, user).

        Raises:
            AuthenticationError: if credentials are invalid or account is inactive.
        """
        result = await self._db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated. Contact your administrator.")

        access_token = create_access_token(
            user_id=str(user.id),
            role=user.role.value,
            token_version=user.token_version,
        )
        refresh_token = create_refresh_token(
            user_id=str(user.id),
            token_version=user.token_version,
        )
        return access_token, refresh_token, user

    async def logout(self, user: User) -> None:
        """
        Invalidate all active tokens for this user by incrementing token_version.
        """
        user.token_version += 1
        await self._db.commit()

    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Validate a refresh token and issue a new access token.

        Raises:
            AuthenticationError: if the token is invalid, expired, or version mismatched.
        """
        import uuid
        from jose import JWTError

        try:
            payload = decode_refresh_token(refresh_token)
        except JWTError as exc:
            raise AuthenticationError(f"Invalid refresh token: {exc}") from exc

        user_id_str = payload.get("sub")
        token_version = payload.get("tv")

        if not user_id_str:
            raise AuthenticationError("Token is missing subject claim.")

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError as exc:
            raise AuthenticationError("Invalid user ID in token.") from exc

        result = await self._db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise AuthenticationError("User not found or account is inactive.")

        if user.token_version != token_version:
            raise AuthenticationError(
                "Token has been invalidated. Please log in again."
            )

        return create_access_token(
            user_id=str(user.id),
            role=user.role.value,
            token_version=user.token_version,
        )
