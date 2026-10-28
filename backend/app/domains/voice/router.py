import base64
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.stt import get_stt_provider
from app.ai.providers.tts import get_tts_provider
from app.core.database import get_db
from app.domains.auth.dependencies import verify_caregiver_patient_access, verify_patient_self_or_caregiver_access
from app.domains.voice.live_socket import handle_voice_websocket
from app.domains.voice.schemas import (
    AskAssistantRequest,
    AskAssistantResponse,
    AssistantPayload,
    AudioPayload,
    ConversationResponse,
    MessageItemResponse,
    SynthesizeSpeechRequest,
    SynthesizeSpeechResponse,
    TranscribeAudioResponse,
    TranscriptPayload,
    VoiceConverseResponse,
)
from app.domains.voice.service import VoiceAssistantService

router = APIRouter(tags=["Voice & Assistant"])


@router.post(
    "/patients/{patient_id}/conversations/message",
    response_model=AskAssistantResponse,
    status_code=200,
    summary="Ask the AI Assistant a question (Voice / Text)",
)
async def ask_assistant(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    body: AskAssistantRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AskAssistantResponse:
    """
    Submits a spoken or typed question to the Personalized Memory Engine (PME).
    Returns a grounded answer with explicit provenance sources and confidence scoring.
    """
    service = VoiceAssistantService(db)
    return await service.process_turn(patient_id, body)


@router.post(
    "/patients/{patient_id}/voice/transcribe",
    response_model=TranscribeAudioResponse,
    summary="Transcribe spoken audio bytes to text (STT)",
)
async def transcribe_audio(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    audio: UploadFile = File(...),
    language_code: str = Form(default="en-IN"),
) -> TranscribeAudioResponse:
    """Converts recorded audio from the patient's device into text."""
    audio_bytes = await audio.read()
    if not audio_bytes or len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file cannot be empty.",
        )
    try:
        stt = get_stt_provider()
        text = await stt.transcribe(audio_bytes=audio_bytes, language_code=language_code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not transcribe audio. The audio format may be corrupted or invalid.",
        )
    return TranscribeAudioResponse(transcript=text, language_code=language_code)


@router.post(
    "/patients/{patient_id}/voice/synthesize",
    response_model=SynthesizeSpeechResponse,
    summary="Synthesize response text to audio (TTS)",
)
async def synthesize_speech(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    body: SynthesizeSpeechRequest,
) -> SynthesizeSpeechResponse:
    """Converts response text into MP3 audio base64 stream."""
    tts = get_tts_provider()
    audio_bytes = await tts.synthesize(
        text=body.text,
        language_code=body.language_code,
        speaking_rate=body.speaking_rate,
    )
    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    return SynthesizeSpeechResponse(audio_base64=b64_audio, format="mp3")


@router.post(
    "/patients/{patient_id}/voice/converse",
    response_model=VoiceConverseResponse,
    summary="End-to-end voice turn (Audio In -> PME Grounding -> Audio Out)",
)
async def voice_converse(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audio: UploadFile = File(...),
    language_code: str = Form(default="en-IN"),
    conversation_id: str | None = Form(default=None),
) -> VoiceConverseResponse:
    """
    Complete conversational voice turn:
    1. Transcribe incoming microphone audio (STT)
    2. Ground against patient memories (PME)
    3. Synthesize warm compassionate speech (TTS)
    """
    audio_bytes = await audio.read()
    if not audio_bytes or len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file cannot be empty.",
        )
    try:
        stt = get_stt_provider()
        transcript = await stt.transcribe(audio_bytes=audio_bytes, language_code=language_code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not transcribe audio. The audio format may be corrupted or invalid.",
        )

    conv_uuid = uuid.UUID(conversation_id) if conversation_id else None
    req = AskAssistantRequest(
        query=transcript or "Namaste",
        conversation_id=conv_uuid,
        language_code=language_code,
    )

    service = VoiceAssistantService(db)
    res = await service.process_turn(patient_id, req)

    # Synthesize audio with safe fallback (audio failure does not break response)
    audio_b64 = None
    try:
        tts = get_tts_provider()
        tts_bytes = await tts.synthesize(text=res.reply, language_code=language_code)
        if tts_bytes:
            audio_b64 = base64.b64encode(tts_bytes).decode("utf-8")
    except Exception:
        audio_b64 = None

    return VoiceConverseResponse(
        conversation_id=res.conversation_id,
        transcript=transcript,
        transcript_info=TranscriptPayload(text=transcript),
        answer=res.answer,
        reply=res.reply,
        intent=res.intent,
        confidence=res.confidence,
        confidence_info=res.confidence_info,
        assistant=AssistantPayload(
            answer=res.answer,
            reply=res.reply,
            intent=res.intent,
            grounded=res.grounded,
            confidence=res.confidence_info,
            sources=res.sources,
        ),
        sources=res.sources,
        grounded=res.grounded,
        audio=AudioPayload(
            available=audio_b64 is not None,
            format="mp3",
            audio_base64=audio_b64,
        ),
        audio_base64=audio_b64,
        created_at=res.created_at,
    )


@router.get(
    "/patients/{patient_id}/conversations",
    response_model=list[ConversationResponse],
    summary="Get conversation history for a patient",
)
async def list_conversations(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=10, le=50),
) -> list[ConversationResponse]:
    service = VoiceAssistantService(db)
    convs = await service.list_conversations(patient_id, limit=limit)

    results = []
    for c in convs:
        c_dict = ConversationResponse.model_validate(c)
        c_dict.messages = [MessageItemResponse.model_validate(m) for m in c.messages]
        results.append(c_dict)
    return results


@router.get(
    "/patients/{patient_id}/assistant/conversations",
    response_model=list[ConversationResponse],
    summary="Get conversation history for a patient (alias)",
)
async def list_assistant_conversations(
    patient_id: Annotated[uuid.UUID, Depends(verify_patient_self_or_caregiver_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=10, le=50),
) -> list[ConversationResponse]:
    return await list_conversations(patient_id=patient_id, db=db, limit=limit)


@router.websocket("/voice/live")
async def websocket_voice_endpoint(websocket: WebSocket) -> None:
    """
    Real-Time WebSocket Voice Gateway.
    Supports sub-second bidirectional speech, in-memory VAD,
    PME vector memory retrieval, and immediate barge-in interruption.
    """
    await handle_voice_websocket(websocket)


