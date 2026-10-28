"""
CogniCompanion — Auth Dependencies
=====================================
FastAPI dependency functions for JWT validation and RBAC.

Usage:
    from app.domains.auth.dependencies import (
        get_current_user,
        require_role,
        get_current_caregiver,
        get_current_patient,
    )
"""

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, ForbiddenError
from app.core.security import decode_access_token
from app.domains.patients.models import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Extract and validate the Bearer JWT from the Authorization header.

    Validates:
      1. Token signature + expiry (via jose)
      2. Token type is "access"
      3. token_version matches the stored value (detects forced logout)
      4. User exists and is active

    Returns:
        The authenticated User ORM object.

    Raises:
        AuthenticationError: for any validation failure.
    """
    if not credentials:
        raise AuthenticationError("No authentication token provided.")

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError as exc:
        raise AuthenticationError(f"Invalid token: {exc}") from exc

    user_id_str: str | None = payload.get("sub")
    token_version: int | None = payload.get("tv")

    if not user_id_str:
        raise AuthenticationError("Token is missing subject claim.")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError as exc:
        raise AuthenticationError("Token subject is not a valid UUID.") from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise AuthenticationError("User not found or account is deactivated.")

    if user.token_version != token_version:
        raise AuthenticationError("Session has been invalidated. Please log in again.")

    return user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory that restricts access to specific roles.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            _: User = Depends(require_role(UserRole.ADMIN))
        ):
            ...
    """
    async def _check_role(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed_roles:
            raise ForbiddenError(
                f"This action requires one of the following roles: "
                f"{', '.join(r.value for r in allowed_roles)}."
            )
        return user

    return _check_role


async def get_current_caregiver(
    user: Annotated[User, Depends(require_role(UserRole.CAREGIVER, UserRole.ADMIN))],
) -> User:
    """Shorthand dependency — requires CAREGIVER or ADMIN role."""
    return user


async def get_current_patient(
    user: Annotated[User, Depends(require_role(UserRole.PATIENT))],
) -> User:
    """Shorthand dependency — requires PATIENT role."""
    return user


async def verify_caregiver_patient_access(
    patient_id: uuid.UUID,
    caregiver: Annotated[User, Depends(get_current_caregiver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> uuid.UUID:
    """
    Verify that the authenticated caregiver is assigned to the requested patient.

    This is the core authorization gate for all caregiver→patient data access.
    ADMINs bypass the check.

    Returns:
        patient_id if access is authorized.

    Raises:
        ForbiddenError: if the caregiver is not assigned to this patient.
    """
    from app.domains.patients.models import CaregiverPatient, Patient

    if caregiver.role == UserRole.ADMIN:
        return patient_id

    result = await db.execute(
        select(CaregiverPatient).where(
            CaregiverPatient.caregiver_id == caregiver.id,
            CaregiverPatient.patient_id == patient_id,
        )
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise ForbiddenError("You are not assigned to this patient.")

    return patient_id


async def verify_patient_self_or_caregiver_access(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> uuid.UUID:
    """
    Flexible authorization gate used by endpoints the **patient app** calls.

    Allows access when:
      - Role is ADMIN  → always allowed.
      - Role is CAREGIVER → must be assigned to this patient (existing rule).
      - Role is PATIENT  → the authenticated user's Patient record must match
                           the requested patient_id.  A patient cannot access
                           another patient's data.

    Returns:
        patient_id if access is authorized.

    Raises:
        ForbiddenError: if the requesting user has no authority over this patient.
        AuthenticationError: propagated from get_current_user if JWT is invalid.
    """
    from app.domains.patients.models import CaregiverPatient, Patient, UserRole

    if current_user.role == UserRole.ADMIN:
        return patient_id

    if current_user.role == UserRole.PATIENT:
        # Verify the authenticated user IS the patient being requested.
        result = await db.execute(
            select(Patient).where(
                Patient.id == patient_id,
                Patient.user_id == current_user.id,
            )
        )
        patient = result.scalar_one_or_none()
        if not patient:
            raise ForbiddenError("You can only access your own patient record.")
        return patient_id

    # CAREGIVER (or DOCTOR) — must be assigned to this patient or own self patient profile.
    result = await db.execute(
        select(CaregiverPatient).where(
            CaregiverPatient.caregiver_id == current_user.id,
            CaregiverPatient.patient_id == patient_id,
        )
    )
    assignment = result.scalar_one_or_none()
    if assignment:
        return patient_id

    # Allow caregiver accessing their own auto-provisioned test patient record
    own_patient = await db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.user_id == current_user.id,
        )
    )
    if own_patient.scalar_one_or_none():
        return patient_id

    raise ForbiddenError("You are not assigned to this patient.")
