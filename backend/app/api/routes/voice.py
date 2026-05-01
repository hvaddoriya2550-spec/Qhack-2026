import base64
import os

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from google import genai
from google.genai import types as genai_types

from app.core.config import settings
from app.db.session import get_db
from app.schemas.voice import TranscriptionResponse
from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest

router = APIRouter()


# ── Gemini STT ─────────────────────────────────────────────────────

async def _transcribe_with_gemini(audio_bytes: bytes, filename: str) -> str:
    """Transcribe audio using Gemini's multimodal capabilities."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    ext = os.path.splitext(filename)[1].lower()
    mime_map = {".webm": "audio/webm", ".wav": "audio/wav", ".mp3": "audio/mp3", ".ogg": "audio/ogg"}
    mime_type = mime_map.get(ext, "audio/webm")

    audio_part = genai_types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)

    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            audio_part,
            "Transcribe this audio exactly as spoken. "
            "Return only the transcription, nothing else.",
        ],
    )
    return response.text.strip()


# ── Voice Summary ──────────────────────────────────────────────

async def _summarize_for_voice(text: str) -> str:
    """Summarize a long agent response into a concise spoken version."""
    from app.agents.base.llm import chat_completion

    response = await chat_completion(
        model="gemini-2.5-flash",
        system=(
            "You are Cleo, a voice assistant. Summarize the following agent "
            "response into 2-3 natural spoken sentences. Be conversational "
            "and friendly. Mention the key takeaway and tell the user they "
            "can read the full details in the chat. Do NOT use markdown, "
            "bullet points, or formatting — just plain spoken sentences."
        ),
        messages=[{"role": "user", "content": text}],
        max_tokens=256,
    )
    summary = response.text.strip()
    return summary if summary else text[:300] + "... You can read the full details in the chat."


# ── ElevenLabs TTS ─────────────────────────────────────────────────

async def _elevenlabs_tts(text: str) -> bytes:
    """Convert text to speech using ElevenLabs. Returns MP3 bytes."""
    from elevenlabs import AsyncElevenLabs

    client = AsyncElevenLabs(api_key=settings.ELEVENLABS_API_KEY)

    audio_iter = await client.text_to_speech.convert(
        voice_id=settings.ELEVENLABS_VOICE_ID,
        text=text,
        model_id="eleven_turbo_v2_5",
        output_format="mp3_44100_128",
    )

    # Collect all chunks into bytes
    chunks = []
    async for chunk in audio_iter:
        chunks.append(chunk)
    return b"".join(chunks)


# ── Routes ─────────────────────────────────────────────────────────

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
) -> TranscriptionResponse:
    """Transcribe audio to text using Gemini."""
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")

    audio_bytes = await audio.read()
    text = await _transcribe_with_gemini(audio_bytes, audio.filename or "audio.webm")
    return TranscriptionResponse(text=text)


@router.post("/tts")
async def text_to_speech(body: dict) -> Response:
    """Convert text to speech using ElevenLabs. Returns MP3 audio."""
    if not settings.ELEVENLABS_API_KEY:
        raise HTTPException(status_code=503, detail="ElevenLabs API key not configured")

    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    try:
        audio_bytes = await _elevenlabs_tts(text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TTS failed: {e}")

    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/chat")
async def voice_chat(
    audio: UploadFile = File(...),
    conversation_id: str | None = None,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Full voice round-trip: Gemini STT → agent → ElevenLabs TTS.

    Returns JSON with transcript, reply text, and base64 audio (if ElevenLabs is configured).
    """
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")

    # Step 1: Transcribe
    audio_bytes = await audio.read()
    if len(audio_bytes) < 100:
        raise HTTPException(status_code=400, detail="Audio too short")
    try:
        user_text = await _transcribe_with_gemini(
            audio_bytes, audio.filename or "audio.webm"
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {e}")

    # Step 2: Agent pipeline
    service = ChatService(db=db)
    chat_response = await service.process_message(
        ChatRequest(
            conversation_id=conversation_id,
            project_id=project_id,
            message=user_text,
        )
    )

    full_reply = chat_response.message

    # Step 3: Summarize long responses for voice
    spoken_text = full_reply
    if len(full_reply) > 400:
        spoken_text = await _summarize_for_voice(full_reply)

    result = {
        "transcript": user_text,
        "reply": full_reply,
        "spoken_summary": spoken_text,
        "conversation_id": chat_response.conversation_id,
        "agent_name": chat_response.metadata.get("agent_name"),
        "phase": chat_response.metadata.get("phase"),
        "metadata": chat_response.metadata,
    }

    # Step 4: TTS with ElevenLabs (if configured) — use spoken summary
    if settings.ELEVENLABS_API_KEY:
        try:
            tts_bytes = await _elevenlabs_tts(spoken_text)
            result["audio_base64"] = base64.b64encode(tts_bytes).decode()
        except Exception:
            result["audio_base64"] = None

    return result
