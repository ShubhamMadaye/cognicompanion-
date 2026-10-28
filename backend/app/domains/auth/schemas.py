"""
CogniCompanion — Auth Domain Schemas
=======================================
Pydantic v2 request/response models for authentication & registration.
"""

from pydantic import BaseModel, EmailStr, Field

from app.domains.patients.models import UserRole
from app.domains.patients.schemas import UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    full_name: str = Field(min_length=2, max_length=200)
    role: UserRole = UserRole.CAREGIVER


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully"
