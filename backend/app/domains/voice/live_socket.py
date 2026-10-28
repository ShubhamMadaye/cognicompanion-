"""
CogniCompanion — Real-Time WebSocket Voice & Barge-In Gateway
==============================================================
Provides a persistent bidirectional WebSocket connection for continuous speech:
  - Sub-millisecond VAD audio frame processing
  - Real-time barge-in cancellation when user speaks during assistant playback
  - Memory-grounded streaming answers via the Personalized Memory Engine (PME)
  - Audio chunk delivery for uninterrupted playback
"""

import asyncio
import base64
import json
import logging
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.stt import get_stt_provider
from app.ai.providers.tts import get_tts_provider
from app.core.database import AsyncSessionLocal
from app.domains.voice.schemas import AskAssistantRequest
from app.domains.voice.service import VoiceAssistantService
from app.domains.voice.vad import FrameVAD

logger = logging.getLogger(__name__)


from app.ai.languages.language_identifier import detect_language_from_text

def _detect_script_language(text: str, current_lang: str) -> str:
    """Detects regional/Northeast Indian language using language_identifier."""
    return detect_language_from_text(text, current_language=current_lang)


class LiveVoiceSession:
    """Manages a single real-time conversational voice session."""

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self.vad = FrameVAD()
        self.patient_id: uuid.UUID | None = None
        self.language_code: str = "en-IN"
        self.conversation_id: uuid.UUID | None = None

        self.state: str = "IDLE"  # IDLE, LISTENING, PROCESSING, SPEAKING
        self._audio_buffer: bytearray = bytearray()
        self._active_speech_task: asyncio.Task | None = None

    async def handle(self) -> None:
        await self.websocket.accept()
        await self._send_json({
            "type": "SESSION_READY",
            "message": "CogniCompanion Real-Time Voice Gateway connected.",
            "capabilities": ["barge_in", "vector_memory_rag", "pcm_streaming"],
        })
        self.state = "LISTENING"

        try:
            while True:
                message = await self.websocket.receive()

                # 1. Binary message: Raw 16kHz PCM audio chunk
                if "bytes" in message and message["bytes"]:
                    pcm_chunk = message["bytes"]
                    await self._handle_pcm_chunk(pcm_chunk)

                # 2. Text message: JSON control event
                elif "text" in message and message["text"]:
                    data = json.loads(message["text"])
                    await self._handle_control_event(data)

        except WebSocketDisconnect:
            logger.info("[LiveVoice] WebSocket disconnected by client.")
        except Exception as e:
            logger.error("[LiveVoice] Error in session: %s", e)
        finally:
            if self._active_speech_task and not self._active_speech_task.done():
                self._active_speech_task.cancel()

    async def _handle_pcm_chunk(self, chunk: bytes) -> None:
        # Check for Barge-in Interruption if assistant is currently speaking
        if self.state == "SPEAKING":
            is_voiced, _ = self.vad.process_frame(chunk)
            if is_voiced:
                logger.info("[LiveVoice] Barge-in detected! Halting assistant audio output.")
                if self._active_speech_task and not self._active_speech_task.done():
                    self._active_speech_task.cancel()

                self.state = "LISTENING"
                self._audio_buffer.clear()
                self.vad.reset()

                await self._send_json({
                    "type": "INTERRUPTED",
                    "reason": "User started speaking (barge-in)",
                })
                return

        # Regular listening accumulation
        if self.state == "LISTENING":
            self._audio_buffer.extend(chunk)
            is_speaking, turn_completed = self.vad.process_frame(chunk)

            if is_speaking:
                await self._send_json({"type": "USER_SPEAKING"})

            if turn_completed and len(self._audio_buffer) > 3200:  # At least 100ms
                await self._process_accumulated_audio()

    async def _handle_control_event(self, data: dict) -> None:
        event_type = data.get("type")

        if event_type == "START_SESSION":
            raw_id = data.get("patient_id")
            if raw_id:
                try:
                    self.patient_id = uuid.UUID(str(raw_id))
                except ValueError:
                    self.patient_id = None
            if not self.patient_id:
                await self._send_json({
                    "type": "ERROR",
                    "code": "INVALID_PATIENT_ID",
                    "message": "A valid patient_id UUID is required to start a voice session.",
                })
                return
            self.language_code = data.get("language_code", "en-IN")
            self.vad.reset()
            self._audio_buffer.clear()
            self.state = "LISTENING"
            await self._send_json({
                "type": "LISTENING",
                "language_code": self.language_code,
                "patient_id": str(self.patient_id),
            })

        elif event_type == "TEXT_QUERY":
            query = data.get("query", "").strip()
            image_base64 = data.get("image_base64")
            req_lang = data.get("language_code")
            if req_lang:
                self.language_code = req_lang
            if query:
                self.language_code = _detect_script_language(query, self.language_code)
            if query or image_base64:
                effective_query = query if query else "What is this in the image?"
                await self._process_query(effective_query, image_base64=image_base64)

        elif event_type == "BARGE_IN_INTERRUPT":
            # Client-side audio cut-off event
            if self._active_speech_task and not self._active_speech_task.done():
                self._active_speech_task.cancel()
            self.state = "LISTENING"
            self.vad.reset()
            self._audio_buffer.clear()
            await self._send_json({"type": "INTERRUPTED", "reason": "client_barge_in"})

    async def _process_accumulated_audio(self) -> None:
        self.state = "PROCESSING"
        audio_to_transcribe = bytes(self._audio_buffer)
        self._audio_buffer.clear()
        self.vad.reset()

        await self._send_json({"type": "PROCESSING", "message": "Transcribing speech..."})

        try:
            stt = get_stt_provider()
            transcript = await stt.transcribe(audio_to_transcribe, language_code=self.language_code)

            if not transcript or not transcript.strip():
                self.state = "LISTENING"
                await self._send_json({"type": "LISTENING", "message": "No speech detected"})
                return

            await self._send_json({"type": "USER_TRANSCRIPT", "transcript": transcript})
            await self._process_query(transcript)
        except Exception as e:
            logger.error("[LiveVoice] Transcription error: %s", e)
            self.state = "LISTENING"
            await self._send_json({"type": "ERROR", "message": "Transcription failed"})

    async def _process_query(self, query: str, image_base64: str | None = None) -> None:
        self.state = "PROCESSING"
        await self._send_json({"type": "PROCESSING", "message": "Searching memory & generating answer..."})

        # Run assistant processing in a cancellable task so barge-in can halt it instantly
        self._active_speech_task = asyncio.create_task(
            self._run_assistant_turn(query, image_base64=image_base64)
        )

    async def _run_assistant_turn(self, query: str, image_base64: str | None = None) -> None:
        async with AsyncSessionLocal() as db:
            try:
                service = VoiceAssistantService(db)
                req = AskAssistantRequest(
                    query=query,
                    conversation_id=self.conversation_id,
                    language_code=self.language_code,
                    image_base64=image_base64,
                )

                # Enforce strict patient session isolation — reject unauthenticated requests
                if not self.patient_id:
                    logger.warning("[LiveVoice] Assistant turn attempted without active patient_id session.")
                    await self._send_json({
                        "type": "ERROR",
                        "code": "SESSION_NOT_INITIALIZED",
                        "message": "No active patient session established. Send START_SESSION with valid patient_id.",
                    })
                    return

                target_patient_id = self.patient_id
                response = await service.process_turn(target_patient_id, req)

                self.conversation_id = response.conversation_id
                self.state = "SPEAKING"

                # Send structured transcript response first for instant display
                await self._send_json({
                    "type": "ASSISTANT_REPLY",
                    "text": response.answer,
                    "intent": response.intent,
                    "confidence": response.confidence,
                    "sources": [
                        {"type": s.source_type, "title": s.title} for s in response.sources
                    ],
                    "conversation_id": str(response.conversation_id),
                })

                # Synthesize and stream speech audio
                tts = get_tts_provider()
                audio_bytes = await tts.synthesize(
                    text=response.answer,
                    language_code=self.language_code,
                )

                if audio_bytes:
                    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                    await self._send_json({
                        "type": "AUDIO_CHUNK",
                        "audio_base64": b64_audio,
                    })

                await self._send_json({"type": "TURN_FINISHED"})
            except asyncio.CancelledError:
                logger.info("[LiveVoice] Assistant turn cancelled due to user barge-in.")
                return
            except Exception as e:
                logger.error("[LiveVoice] Error generating assistant reply: %s", e)
                await self._send_json({"type": "ERROR", "message": "Failed to generate reply"})
            finally:
                if self.state != "LISTENING":
                    self.state = "LISTENING"
                    self.vad.reset()

    async def _send_json(self, payload: dict) -> None:
        try:
            await self.websocket.send_text(json.dumps(payload))
        except Exception:
            pass


async def handle_voice_websocket(websocket: WebSocket) -> None:
    """Entrypoint called by FastAPI websocket route."""
    session = LiveVoiceSession(websocket)
    await session.handle()
