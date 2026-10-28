"""
CogniCompanion — Auth Tests
==============================
Tests for login, register, refresh, and logout endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.patients.models import User


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, caregiver_user: User) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "caregiver@test.com", "password": "TestPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, caregiver_user: User) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "caregiver@test.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@nowhere.com", "password": "TestPass123!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient, caregiver_user: User) -> None:
    # Login first
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "caregiver@test.com", "password": "TestPass123!"},
    )
    token = login_resp.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "caregiver@test.com"
    assert data["role"] == "CAREGIVER"


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, caregiver_user: User) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "caregiver@test.com", "password": "TestPass123!"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


@pytest.mark.asyncio
async def test_login_returns_user_info(client: AsyncClient, caregiver_user: User) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "caregiver@test.com", "password": "TestPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert data["user"]["email"] == "caregiver@test.com"
    assert data["user"]["role"] == "CAREGIVER"


@pytest.mark.asyncio
async def test_register_caregiver_success(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "new.caregiver@example.com",
            "password": "SecurePassword123!",
            "full_name": "Rohan Mehta",
            "role": "CAREGIVER",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "new.caregiver@example.com"
    assert data["user"]["full_name"] == "Rohan Mehta"
    assert data["user"]["role"] == "CAREGIVER"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, caregiver_user: User) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "caregiver@test.com",
            "password": "AnotherPassword123!",
            "full_name": "Duplicate User",
            "role": "CAREGIVER",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_logout_invalidates_tokens(client: AsyncClient, caregiver_user: User) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "caregiver@test.com", "password": "TestPass123!"},
    )
    token = login_resp.json()["access_token"]
    refresh_token = login_resp.json()["refresh_token"]

    # Logout
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_resp.status_code == 200

    # Trying to use old refresh token should fail
    refresh_attempt = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_attempt.status_code == 401

