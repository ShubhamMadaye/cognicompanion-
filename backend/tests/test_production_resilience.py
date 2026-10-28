"""
CogniCompanion — Production Resilience & Security Audit Suite
=============================================================
Production verification gate covering:
  - Phase 2: Voice Pipeline Transitions
  - Phase 3: Security & IDOR Cross-Patient Isolation
  - Phase 4: Chaos & External AI (Gemini) Failure Fallback
  - Phase 5: Voice / Cloud TTS Outage & Device Fallback
  - Phase 6: Bad / Corrupted Audio Payload Defense
  - Phase 7: Request Protection (15 MiB Boundary & 429 Rate Limiting)
  - Phase 8: Immediate Token Revocation via token_version
  - Phase 9: Clinical Missing-Data Absence Safety
  - Phase 10: Production Configuration Integrity
"""

import base64
import io
import uuid
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rate_limiter import rate_limiter
from app.core.security import create_access_token
from app.domains.memories.models import Memory, MemoryType, Person
from app.domains.patients.models import CaregiverPatient, Patient, User, UserRole
from app.domains.timeline.models import Medication, MedicationFrequency, MedicationTiming


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
async def second_patient(db: AsyncSession) -> Patient:
    """Creates an isolated second patient for IDOR testing."""
    user = User(
        id=uuid.uuid4(),
        email=f"patient_b_{uuid.uuid4().hex[:6]}@test.com",
        full_name="Patient B User",
        hashed_password="hashed_pw_test",
        role=UserRole.PATIENT,
        token_version=0,
    )
    db.add(user)
    await db.flush()

    p = Patient(
        id=uuid.uuid4(),
        user_id=user.id,
        date_of_birth=date(1948, 5, 12),
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


# ── Test Classes ──────────────────────────────────────────────────────────────

class TestSecurityHeaders:
    """Phase 3 / Security: Verifies OWASP recommended security headers."""

    @pytest.mark.asyncio
    async def test_security_headers_enforced(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        h = resp.headers
        assert h.get("x-frame-options") == "DENY"
        assert h.get("x-content-type-options") == "nosniff"
        assert h.get("x-xss-protection") == "1; mode=block"
        assert "strict-origin" in h.get("referrer-policy", "")
        assert "content-security-policy" in h
        assert "camera=()" in h.get("permissions-policy", "")


class TestRateLimiting:
    """Phase 7: Verifies sliding-window rate limiting triggers HTTP 429."""

    @pytest.mark.asyncio
    async def test_burst_rate_limit_triggers_429(self, client: AsyncClient) -> None:
        rate_limiter.clear()

        # Auth threshold is 15 requests per minute
        for _ in range(15):
            r = await client.post(
                "/api/v1/auth/login",
                json={"email": "nonexistent@test.com", "password": "WrongPassword1!"},
            )
            assert r.status_code in (401, 200)

        # 16th burst request must be blocked
        blocked = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@test.com", "password": "WrongPassword1!"},
        )
        assert blocked.status_code == 429
        assert "retry_after_seconds" in blocked.json()
        assert "Retry-After" in blocked.headers

        rate_limiter.clear()


class TestRequestSizeLimit:
    """Phase 7: Verifies 15 MiB request body protection boundary."""

    @pytest.mark.asyncio
    async def test_oversized_payload_rejected_413(self, client: AsyncClient) -> None:
        # > 15 MB content length
        resp = await client.post(
            "/api/v1/auth/login",
            headers={"Content-Length": str(16 * 1024 * 1024)},
            content=b"x" * 10,
        )
        assert resp.status_code == 413
        assert "payload too large" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_acceptable_payload_size_passed(self, client: AsyncClient) -> None:
        # Normal content length < 15MB does not trigger 413
        resp = await client.post(
            "/api/v1/auth/login",
            headers={"Content-Length": "100"},
            json={"email": "nonexistent@test.com", "password": "WrongPassword1!"},
        )
        assert resp.status_code != 413


class TestPatientIsolation:
    """Phase 3: IDOR & Cross-Tenant Access Control."""

    @pytest.mark.asyncio
    async def test_patient_cannot_access_another_patient_timeline(
        self, client: AsyncClient, patient: Patient, second_patient: Patient
    ) -> None:
        """Patient A cannot read Patient B's timeline (403 Forbidden)."""
        token_a = create_access_token(
            user_id=str(patient.user_id),
            role=UserRole.PATIENT.value,
            token_version=0,
        )
        headers_a = {"Authorization": f"Bearer {token_a}"}

        resp = await client.get(
            f"/api/v1/patients/{second_patient.id}/timeline",
            headers=headers_a,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_patient_cannot_query_another_patient_assistant(
        self, client: AsyncClient, patient: Patient, second_patient: Patient
    ) -> None:
        """Patient A cannot trigger PME queries against Patient B (403 Forbidden)."""
        token_a = create_access_token(
            user_id=str(patient.user_id),
            role=UserRole.PATIENT.value,
            token_version=0,
        )
        headers_a = {"Authorization": f"Bearer {token_a}"}

        resp = await client.post(
            f"/api/v1/patients/{second_patient.id}/conversations/message",
            headers=headers_a,
            json={"query": "Who visited me yesterday?"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unlinked_caregiver_cannot_access_patient(
        self, client: AsyncClient, auth_headers: dict, second_patient: Patient
    ) -> None:
        """Caregiver A cannot access unlinked Patient B (403 Forbidden)."""
        resp = await client.get(
            f"/api/v1/patients/{second_patient.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 403


class TestTokenRevocation:
    """Phase 8: Token revocation on token_version mismatch."""

    @pytest.mark.asyncio
    async def test_revoked_token_immediately_rejected(
        self, client: AsyncClient, db: AsyncSession, caregiver_user: User, patient: Patient
    ) -> None:
        token = create_access_token(
            user_id=str(caregiver_user.id),
            role=caregiver_user.role.value,
            token_version=caregiver_user.token_version,
        )
        headers = {"Authorization": f"Bearer {token}"}

        # Valid initially
        r1 = await client.get(f"/api/v1/patients/{patient.id}", headers=headers)
        assert r1.status_code == 200

        # Invalidate by bumping version
        caregiver_user.token_version += 1
        await db.commit()

        # Rejected immediately
        r2 = await client.get(f"/api/v1/patients/{patient.id}", headers=headers)
        assert r2.status_code == 401
        assert "invalidated" in r2.json()["detail"].lower()


class TestGeminiFailure:
    """Phase 4: Chaos testing — External Gemini API outage/timeout."""

    @pytest.mark.asyncio
    async def test_gemini_outage_falls_back_to_deterministic_grounding(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, db: AsyncSession
    ) -> None:
        """When Gemini throws an outage/timeout, PME falls back to deterministic template without crashing."""
        p = Person(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Rahul",
            relationship="Son",
            description="Lives in Pune.",
        )
        db.add(p)
        await db.commit()

        with patch("google.generativeai.GenerativeModel.generate_content_async", side_effect=TimeoutError("Gemini unavailable")):
            resp = await client.post(
                f"/api/v1/patients/{patient.id}/conversations/message",
                headers=auth_headers,
                json={"query": "Who is Rahul?"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["grounded"] is True
        assert "Rahul" in data["answer"]
        assert data["confidence_info"]["level"] in ("HIGH", "MEDIUM")


class TestSpeechFailure:
    """Phase 5: Cloud TTS Outage & Device-TTS Fallback."""

    @pytest.mark.asyncio
    async def test_cloud_tts_outage_preserves_grounded_answer(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ) -> None:
        """If cloud TTS fails, /voice/converse still succeeds and delivers text answer with audio=null."""
        audio_content = b"Who is Rahul?"
        files = {"audio": ("query.wav", io.BytesIO(audio_content), "audio/wav")}

        with patch("app.ai.providers.tts.MockTTSProvider.synthesize", side_effect=Exception("TTS Network Error")):
            resp = await client.post(
                f"/api/v1/patients/{patient.id}/voice/converse",
                headers=auth_headers,
                files=files,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] != ""
        assert data["audio_base64"] is None
        assert data["audio"]["available"] is False


class TestMalformedAudio:
    """Phase 6: Malformed / Bad Audio Payload Defense (Never 500)."""

    @pytest.mark.asyncio
    async def test_empty_audio_file_returns_400(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ) -> None:
        """Empty audio bytes return 400 Bad Request, never 500."""
        files = {"audio": ("empty.wav", io.BytesIO(b""), "audio/wav")}
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/voice/transcribe",
            headers=auth_headers,
            files=files,
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_corrupted_audio_in_converse_returns_400_or_422(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ) -> None:
        """Corrupted audio payload in converse returns 400, never 500."""
        files = {"audio": ("bad.wav", io.BytesIO(b""), "audio/wav")}
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/voice/converse",
            headers=auth_headers,
            files=files,
        )
        assert resp.status_code == 400
        assert resp.status_code != 500


class TestMissingData:
    """Phase 9: Missing-Data Clinical Absence Safety (No record != Negative event)."""

    @pytest.mark.asyncio
    async def test_missing_visit_record_does_not_assert_negative_fact(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ) -> None:
        """When no visit exists, response states no record was found rather than inventing negative fact."""
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/conversations/message",
            headers=auth_headers,
            json={"query": "Who visited me yesterday?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        ans = data["answer"].lower()
        # Must distinguish missing record from asserting nobody visited
        assert "couldn't find" in ans or "could not find" in ans or "no record" in ans or "not find" in ans
        assert "nobody visited you" not in ans

    @pytest.mark.asyncio
    async def test_missing_medication_adherence_gives_cautionary_guidance(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, db: AsyncSession
    ) -> None:
        """When medication adherence log is absent, cautions patient and advises checking with caregiver."""
        med = Medication(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Aspirin",
            dosage="75mg",
            frequency=MedicationFrequency.ONCE_DAILY,
            timing=MedicationTiming.AFTER_BREAKFAST,
            is_active=True,
        )
        db.add(med)
        await db.commit()

        resp = await client.post(
            f"/api/v1/patients/{patient.id}/conversations/message",
            headers=auth_headers,
            json={"query": "Did I take my morning medication?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        ans = data["answer"]
        # Safety disclaimer present
        assert "caregiver" in ans.lower() or "not recorded" in ans.lower() or "could not find" in ans.lower()


class TestVoicePipeline:
    """Phase 2: Complete End-to-End Voice Pipeline verification."""

    @pytest.mark.asyncio
    async def test_end_to_end_voice_converse_success(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, db: AsyncSession
    ) -> None:
        p = Person(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Rahul Sharma",
            relationship="Son",
            description="Calls every evening.",
        )
        db.add(p)
        await db.commit()

        audio_content = b"Who is Rahul?"
        files = {"audio": ("query.wav", io.BytesIO(audio_content), "audio/wav")}

        resp = await client.post(
            f"/api/v1/patients/{patient.id}/voice/converse",
            headers=auth_headers,
            files=files,
            data={"language_code": "en-IN"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["transcript"] != ""
        assert "Rahul" in data["answer"]
        assert data["grounded"] is True
        assert data["confidence_info"]["score"] >= 0.85
        assert "transcript_info" in data
        assert "assistant" in data
        assert "audio" in data


class TestProductionConfiguration:
    """Phase 10: Production Configuration Integrity."""

    def test_settings_integrity(self) -> None:
        from app.core.body_size_limit import DEFAULT_MAX_BODY_SIZE

        settings = get_settings()
        assert len(settings.JWT_SECRET) >= 32
        assert settings.API_V1_PREFIX == "/api/v1"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert DEFAULT_MAX_BODY_SIZE >= 15 * 1024 * 1024
