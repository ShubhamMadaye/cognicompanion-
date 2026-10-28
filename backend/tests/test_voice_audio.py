"""
CogniCompanion — Voice Audio & Interaction Pipeline Tests (Phase 5)
===================================================================
Validates:
  - Speech-to-Text audio transcription (STT)
  - Text-to-Speech audio synthesis (TTS)
  - End-to-End voice conversational turn (Converse)
  - Graceful mock provider fallbacks in test/offline environments
  - Non-blocking TTS failures (conversation succeeds even if audio fails)
  - Patient isolation and access control
"""

import base64
import io
import uuid
from datetime import date
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.memories.models import Memory, MemoryType, Person
from app.domains.patients.models import Patient


class TestVoiceAudioPipeline:

    @pytest.mark.asyncio
    async def test_transcription(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """Transcribe audio endpoint converts audio bytes to text."""
        audio_content = b"Who is Rahul?"
        files = {"audio": ("query.wav", io.BytesIO(audio_content), "audio/wav")}

        resp = await client.post(
            f"/api/v1/patients/{patient.id}/voice/transcribe",
            headers=auth_headers,
            files=files,
            data={"language_code": "en-IN"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "transcript" in data
        assert len(data["transcript"]) > 0

    @pytest.mark.asyncio
    async def test_synthesis(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """Synthesize endpoint converts response text to MP3 audio base64."""
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/voice/synthesize",
            headers=auth_headers,
            json={
                "text": "Namaste! Rahul is your loving grandson.",
                "language_code": "en-IN",
                "speaking_rate": 0.9,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "mp3"
        assert len(data["audio_base64"]) > 0

        # Verify decodable base64
        decoded = base64.b64decode(data["audio_base64"])
        assert len(decoded) > 0

    @pytest.mark.asyncio
    async def test_voice_conversation(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, db: AsyncSession
    ):
        """End-to-end voice turn: audio in -> STT -> PME Grounding -> TTS -> audio out."""
        # Seed person memory
        p = Person(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="Rahul",
            relationship="Grandson",
            description="Loves playing cricket.",
        )
        db.add(p)
        await db.flush()

        audio_content = b"Who is Rahul?"
        files = {"audio": ("input.wav", io.BytesIO(audio_content), "audio/wav")}

        resp = await client.post(
            f"/api/v1/patients/{patient.id}/voice/converse",
            headers=auth_headers,
            files=files,
            data={"language_code": "en-IN"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["transcript"] != ""
        assert "Rahul" in data["reply"]
        assert data["confidence"] >= 0.90
        assert len(data["sources"]) >= 1
        assert data["audio_base64"] is not None

    @pytest.mark.asyncio
    async def test_mock_provider_fallback(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """When Google credentials are not set, mock providers execute cleanly without crashing."""
        audio_content = b"What should I do this morning?"
        files = {"audio": ("sample.wav", io.BytesIO(audio_content), "audio/wav")}

        resp = await client.post(
            f"/api/v1/patients/{patient.id}/voice/converse",
            headers=auth_headers,
            files=files,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] != ""
        assert data["conversation_id"] is not None

    @pytest.mark.asyncio
    async def test_tts_failure_does_not_break_conversation(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """If TTS throws an error (e.g. quota/timeout), the conversation still succeeds and returns text."""
        audio_content = b"Namaste"
        files = {"audio": ("sample.wav", io.BytesIO(audio_content), "audio/wav")}

        with patch("app.ai.providers.tts.MockTTSProvider.synthesize", side_effect=Exception("TTS Network Error")):
            resp = await client.post(
                f"/api/v1/patients/{patient.id}/voice/converse",
                headers=auth_headers,
                files=files,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] != ""
        # audio_base64 is None on TTS failure, allowing client device TTS fallback
        assert data["audio_base64"] is None

    @pytest.mark.asyncio
    async def test_voice_conversation_patient_scoping(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Cannot access voice endpoints for a random unlinked patient ID (403 Forbidden)."""
        unauthorized_patient_id = uuid.uuid4()
        audio_content = b"Hello"
        files = {"audio": ("sample.wav", io.BytesIO(audio_content), "audio/wav")}

        resp = await client.post(
            f"/api/v1/patients/{unauthorized_patient_id}/voice/converse",
            headers=auth_headers,
            files=files,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_patient_self_access_voice(
        self, client: AsyncClient, patient: Patient
    ):
        """A patient user can access their own voice endpoints."""
        from app.core.security import create_access_token
        patient_token = create_access_token(
            user_id=str(patient.user_id),
            role="PATIENT",
            token_version=0,
        )
        patient_headers = {"Authorization": f"Bearer {patient_token}"}

        # 1. Transcribe
        files = {"audio": ("sample.wav", io.BytesIO(b"Hello from patient"), "audio/wav")}
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/voice/transcribe",
            headers=patient_headers,
            files=files,
        )
        assert resp.status_code == 200

        # 2. Synthesize
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/voice/synthesize",
            headers=patient_headers,
            json={"text": "Hello patient", "language_code": "en-IN"},
        )
        assert resp.status_code == 200
        assert "audio_base64" in resp.json()

    @pytest.mark.asyncio
    async def test_assamese_voice_turn(
        self, client: AsyncClient, auth_headers: dict, patient: Patient, db: AsyncSession
    ):
        """End-to-end voice turn in Assamese (as-IN)."""
        p = Person(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name="ৰাহুল",
            relationship="নাতি",
            description="নাতি ৰাহুল।",
        )
        db.add(p)
        await db.flush()

        # Simulate WAV audio with RIFF header
        wav_header = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        files = {"audio": ("query.wav", io.BytesIO(wav_header + b"Who is Rahul?"), "audio/wav")}

        resp = await client.post(
            f"/api/v1/patients/{patient.id}/voice/converse",
            headers=auth_headers,
            files=files,
            data={"language_code": "as-IN"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] != ""
        assert data["conversation_id"] is not None
        assert data["audio_base64"] is not None

    @pytest.mark.asyncio
    async def test_meitei_voice_turn(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """End-to-end voice turn in Meitei (mni-IN)."""
        files = {"audio": ("query.wav", io.BytesIO(b"Hello"), "audio/wav")}
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/voice/converse",
            headers=auth_headers,
            files=files,
            data={"language_code": "mni-IN"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] != ""
        assert data["conversation_id"] is not None

    @pytest.mark.asyncio
    async def test_khasi_voice_turn(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """End-to-end voice turn in Khasi (kha-IN)."""
        files = {"audio": ("query.wav", io.BytesIO(b"Kumno"), "audio/wav")}
        resp = await client.post(
            f"/api/v1/patients/{patient.id}/voice/converse",
            headers=auth_headers,
            files=files,
            data={"language_code": "kha-IN"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] != ""
        assert data["conversation_id"] is not None

    @pytest.mark.asyncio
    async def test_multiturn_voice_conversation(
        self, client: AsyncClient, auth_headers: dict, patient: Patient
    ):
        """Multi-turn voice conversation maintains context across consecutive turns."""
        files1 = {"audio": ("turn1.wav", io.BytesIO(b"Namaste"), "audio/wav")}
        resp1 = await client.post(
            f"/api/v1/patients/{patient.id}/voice/converse",
            headers=auth_headers,
            files=files1,
            data={"language_code": "hi-IN"},
        )
        assert resp1.status_code == 200
        conv_id = resp1.json()["conversation_id"]
        assert conv_id is not None

        files2 = {"audio": ("turn2.wav", io.BytesIO(b"Who are you?"), "audio/wav")}
        resp2 = await client.post(
            f"/api/v1/patients/{patient.id}/voice/converse",
            headers=auth_headers,
            files=files2,
            data={"language_code": "hi-IN", "conversation_id": conv_id},
        )
        assert resp2.status_code == 200
        assert resp2.json()["conversation_id"] == conv_id

    def test_voice_live_websocket(self, patient: Patient):
        """Phase 2 WebSocket live voice session connects, initializes, and handles barge-in."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        with client.websocket_connect("/api/v1/voice/live") as ws:
            ready = ws.receive_json()
            assert ready["type"] == "SESSION_READY"

            ws.send_json({
                "type": "START_SESSION",
                "patient_id": str(patient.id),
                "language_code": "en-IN"
            })
            listening = ws.receive_json()
            assert listening["type"] == "LISTENING"

            ws.send_json({"type": "BARGE_IN_INTERRUPT"})
            interrupted = ws.receive_json()
            assert interrupted["type"] == "INTERRUPTED"
