"""
Speech-to-Text (STT) Module

Dual-pipeline STT integration:
- English → OpenAI Whisper API
- Hindi / Hinglish → Sarvam Saaras API
"""

import io
import httpx
import base64
from typing import Optional
from openai import AsyncOpenAI
from server.models import STTResponse, Language
from server.config import settings
from server.language_router import detect_language

# Initialize clients
_openai_client: Optional[AsyncOpenAI] = None


def _get_openai_client() -> AsyncOpenAI:
    """Lazy-initialize OpenAI client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


# ═══════════════════════════════════════════════════════════
# OpenAI Whisper STT (English)
# ═══════════════════════════════════════════════════════════

async def transcribe_openai(audio_bytes: bytes, filename: str = "audio.wav") -> STTResponse:
    """
    Transcribe audio using OpenAI Whisper.
    Best for English audio input.

    Args:
        audio_bytes: Raw audio data
        filename: Filename hint for the API

    Returns:
        STTResponse with transcript and detected language
    """
    try:
        client = _get_openai_client()

        # Create a file-like object from bytes
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename

        response = await client.audio.transcriptions.create(
            model=settings.whisper_model,
            file=audio_file,
            response_format="verbose_json",
            language="en",  # Hint for English
        )

        transcript = response.text.strip()
        detected_lang = getattr(response, 'language', 'en')

        # Determine language
        language = detect_language(transcript, stt_tag=detected_lang)

        return STTResponse(
            transcript=transcript,
            language=language,
            confidence=1.0,
        )

    except Exception as e:
        print(f"[OpenAI STT] Error: {e}")
        return STTResponse(
            transcript="",
            language=Language.ENGLISH,
            confidence=0.0,
        )


# ═══════════════════════════════════════════════════════════
# Sarvam Saaras STT (Hindi / Hinglish)
# ═══════════════════════════════════════════════════════════

async def transcribe_sarvam(audio_bytes: bytes) -> STTResponse:
    """
    Transcribe audio using Sarvam Saaras STT.
    Best for Hindi and Hinglish audio input.

    Args:
        audio_bytes: Raw audio data

    Returns:
        STTResponse with transcript and detected language
    """
    try:
        # Base64 encode the audio
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.sarvam_stt_url,
                headers={
                    "Content-Type": "application/json",
                    "API-Subscription-Key": settings.sarvam_api_key,
                },
                json={
                    "input": audio_b64,
                    "language_code": "hi-IN",
                    "model": "saaras:v2",
                    "with_timestamps": False,
                },
            )

            if response.status_code == 200:
                data = response.json()
                transcript = data.get("transcript", "")

                # Detect if it's pure Hindi or Hinglish
                language = detect_language(transcript, stt_tag="hi")

                return STTResponse(
                    transcript=transcript,
                    language=language,
                    confidence=1.0,
                )
            else:
                print(f"[Sarvam STT] API error: {response.status_code} — {response.text}")
                return STTResponse(
                    transcript="",
                    language=Language.HINDI,
                    confidence=0.0,
                )

    except Exception as e:
        print(f"[Sarvam STT] Error: {e}")
        return STTResponse(
            transcript="",
            language=Language.HINDI,
            confidence=0.0,
        )


# ═══════════════════════════════════════════════════════════
# Auto-Routing STT
# ═══════════════════════════════════════════════════════════

async def transcribe_auto(audio_bytes: bytes, preferred_language: str = "") -> STTResponse:
    """
    Automatically route audio to the best STT engine.

    If preferred_language suggests Hindi, use Sarvam.
    Otherwise, try OpenAI Whisper first.
    If Whisper detects Hindi content, re-route to Sarvam.

    Args:
        audio_bytes: Raw audio data
        preferred_language: Hint from session ("en", "hi", "hi-en")

    Returns:
        STTResponse with transcript and language tag
    """
    if preferred_language in ("hi", "hi-en"):
        # Hindi preference — go straight to Sarvam
        return await transcribe_sarvam(audio_bytes)

    # Default: try Whisper
    result = await transcribe_openai(audio_bytes)

    # If Whisper detected Hindi, re-route to Sarvam for better accuracy
    if result.language in (Language.HINDI, Language.HINGLISH) and result.transcript:
        sarvam_result = await transcribe_sarvam(audio_bytes)
        if sarvam_result.transcript:
            return sarvam_result

    return result
