"""
CogniCompanion — Security Hardening Tests (Phase 11)
=====================================================
Tests for:
  1. Anti-clickjacking, XSS, and MIME-sniffing defense headers
  2. Rate limiting (429 on excessive auth/AI requests)
  3. Payload size limiting (413 on oversized requests)
  4. Instant token revocation on token_version mismatch
  5. XSS input sanitization
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limiter import rate_limiter
from app.core.sanitizer import sanitize_text
from app.core.security import create_access_token
from app.domains.patients.models import Patient, User


@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient) -> None:
    """Every response contains security hardening headers."""
    resp = await client.get("/health")
    assert resp.status_code == 200

    headers = resp.headers
    assert headers["x-frame-options"] == "DENY"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-xss-protection"] == "1; mode=block"
    assert "strict-origin" in headers["referrer-policy"]
    assert "content-security-policy" in headers
    assert "camera=()" in headers["permissions-policy"]


@pytest.mark.asyncio
async def test_token_version_revocation_enforcement(
    client: AsyncClient,
    db: AsyncSession,
    caregiver_user: User,
    patient: Patient,
) -> None:
    """
    When token_version is incremented in the database (forced logout/password reset),
    tokens carrying the old version are rejected immediately with 401.
    """
    # 1. Token carrying current version (0)
    old_token = create_access_token(
        user_id=str(caregiver_user.id),
        role=caregiver_user.role.value,
        token_version=caregiver_user.token_version,
    )
    old_headers = {"Authorization": f"Bearer {old_token}"}

    # Verify old token works initially
    resp1 = await client.get(
        f"/api/v1/patients/{patient.id}",
        headers=old_headers,
    )
    assert resp1.status_code == 200

    # 2. Invalidate session by incrementing token_version
    caregiver_user.token_version += 1
    await db.commit()

    # 3. Old token should now be rejected immediately
    resp2 = await client.get(
        f"/api/v1/patients/{patient.id}",
        headers=old_headers,
    )
    assert resp2.status_code == 401
    assert "invalidated" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_rate_limiting_exceeded(client: AsyncClient) -> None:
    """Exceeding request thresholds triggers 429 Too Many Requests."""
    rate_limiter.clear()

    # Auth limit is 15 requests per minute
    for _ in range(15):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@test.com", "password": "WrongPassword1!"},
        )
        assert resp.status_code in (401, 200)

    # 16th request must be blocked by rate limiter
    blocked_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@test.com", "password": "WrongPassword1!"},
    )
    assert blocked_resp.status_code == 429
    assert "retry_after_seconds" in blocked_resp.json()
    assert "Retry-After" in blocked_resp.headers

    rate_limiter.clear()


@pytest.mark.asyncio
async def test_payload_size_limit_rejection(client: AsyncClient) -> None:
    """Requests exceeding maximum body size are rejected with 413 Payload Too Large."""
    # Send content-length > 15MB
    resp = await client.post(
        "/api/v1/auth/login",
        headers={"Content-Length": "18000000"},
        content=b"x" * 10,
    )
    assert resp.status_code == 413
    assert "payload too large" in resp.json()["detail"].lower()


def test_input_sanitization_removes_xss() -> None:
    """Input sanitizer strips malicious scripts, tags, and event handlers."""
    # Script tag injection
    dirty1 = "<script>alert('xss')</script>Patient feels good"
    assert sanitize_text(dirty1) == "Patient feels good"

    # Iframe injection
    dirty2 = "<iframe src='http://evil.com'></iframe>Medication note"
    assert sanitize_text(dirty2) == "Medication note"

    # Event handler injection
    dirty3 = "<div onmouseover='alert(1)'>Hover me</div>"
    assert "onmouseover" not in (sanitize_text(dirty3) or "")
