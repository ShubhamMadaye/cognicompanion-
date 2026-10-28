"""
CogniCompanion — Test Configuration
=======================================
Pytest fixtures for async DB sessions and test client.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.domains.patients.models import CaregiverPatient, Patient, User, UserRole
# Import all ORM models so SQLAlchemy mapper can resolve cross-domain relationships
import app.domains.memories.models   # noqa: F401
import app.domains.voice.models      # noqa: F401
import app.domains.games.models      # noqa: F401
import app.domains.timeline.models   # noqa: F401
import app.domains.analytics.models  # noqa: F401
from app.main import app as fastapi_app

# ── Test Database (SQLite in-memory for fast tests) ───────────────────────────
# NOTE: For tests that require pgvector, use a real PostgreSQL test DB.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Isolated test DB session — creates tables, yields session, drops tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client with the test DB injected."""
    from httpx import ASGITransport

    async def override_get_db():
        yield db

    fastapi_app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()


# ── User Fixtures ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def caregiver_user(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="caregiver@test.com",
        full_name="Test Caregiver",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.CAREGIVER,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        full_name="Test Admin",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def patient(db: AsyncSession, caregiver_user: User) -> Patient:
    """Creates a Patient + User account and links the caregiver to them."""
    patient_user = User(
        id=uuid.uuid4(),
        email="patient@test.com",
        full_name="Test Patient",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.PATIENT,
    )
    db.add(patient_user)
    await db.flush()

    p = Patient(
        id=uuid.uuid4(),
        user_id=patient_user.id,
        date_of_birth=None,
    )
    db.add(p)
    await db.flush()

    link = CaregiverPatient(
        caregiver_id=caregiver_user.id,
        patient_id=p.id,
        relationship_type="primary",
        is_primary=True,
    )
    db.add(link)
    await db.flush()
    return p


@pytest_asyncio.fixture
async def auth_headers(caregiver_user: User) -> dict[str, str]:
    """Returns Authorization headers for the test caregiver."""
    token = create_access_token(
        user_id=str(caregiver_user.id),
        role=caregiver_user.role.value,
        token_version=caregiver_user.token_version,
    )
    return {"Authorization": f"Bearer {token}"}

