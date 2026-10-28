"""
CogniCompanion — Security Utilities
=====================================
JWT creation/verification and bcrypt password hashing.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# ── Password Hashing ─────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return bcrypt hash of the given plain-text password."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Tokens ────────────────────────────────────────────────────────────────
def _create_token(
    subject: str,
    token_type: str,
    expire_delta: timedelta,
    secret: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Internal helper — create a signed JWT.

    Args:
        subject:      Usually the user's UUID string.
        token_type:   "access" or "refresh" — stored in the "type" claim.
        expire_delta: How long until the token expires.
        secret:       The signing secret (different for access vs refresh).
        extra_claims: Any additional claims to embed (e.g. role, token_version).
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expire_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    user_id: str,
    role: str,
    token_version: int,
) -> str:
    """
    Create a short-lived access JWT.

    Embeds:
        - role          → used for RBAC without a DB lookup on every request
        - token_version → invalidate all tokens on password change / forced logout
    """
    return _create_token(
        subject=user_id,
        token_type="access",
        expire_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        secret=settings.JWT_SECRET,
        extra_claims={"role": role, "tv": token_version},
    )


def create_refresh_token(user_id: str, token_version: int) -> str:
    """
    Create a long-lived refresh JWT.

    Only stores sub + token_version (no role — role is re-fetched on refresh).
    """
    return _create_token(
        subject=user_id,
        token_type="refresh",
        expire_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        secret=settings.JWT_REFRESH_SECRET,
        extra_claims={"tv": token_version},
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate an access token.

    Raises:
        JWTError: if the token is invalid, expired, or wrong type.
    """
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Token type mismatch — expected access token.")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a refresh token.

    Raises:
        JWTError: if the token is invalid, expired, or wrong type.
    """
    payload = jwt.decode(token, settings.JWT_REFRESH_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != "refresh":
        raise JWTError("Token type mismatch — expected refresh token.")
    return payload
