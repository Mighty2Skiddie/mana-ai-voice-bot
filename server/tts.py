"""
Text-to-Speech (TTS) Module

Dual-pipeline TTS integration:
- English → OpenAI TTS with Nova voice (warm, calm, friendly)
- Hindi / Hinglish → Sarvam Bulbul TTS (natural Indian voice)
"""

import io
import base64
import httpx
from typing import Optional
from openai import AsyncOpenAI
from server.config import settings
from server.language_router import detect_language, get_tts_pipeline
from server.models import Language

# Initialize clients
_openai_client: Optional[AsyncOpenAI] = None


def _get_openai_client() -> AsyncOpenAI:
    """Lazy-initialize OpenAI client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


# ═══════════════════════════════════════════════════════════
# OpenAI TTS — Nova Voice (English)
# ═══════════════════════════════════════════════════════════

async def synthesize_openai(text: str) -> bytes:
    """
    Synthesize speech using OpenAI TTS with Nova voice.
    Best for English — warm, soft, and friendly.

    Args:
        text: Text to synthesize

    Returns:
        Audio bytes (MP3 format)
    """
    try:
        client = _get_openai_client()

        response = await client.audio.speech.create(
            model=settings.tts_model,
            voice=settings.tts_voice,  # Nova — warm, calm
            input=text,
            speed=0.95,  # Slightly slower for empathetic pace
        )

        # Read the streaming response into bytes
        audio_bytes = response.content
        return audio_bytes

    except Exception as e:
        print(f"[OpenAI TTS] Error: {e}")
        return b""


# ═══════════════════════════════════════════════════════════
# Sarvam Bulbul TTS (Hindi / Hinglish)
# ═══════════════════════════════════════════════════════════

async def synthesize_sarvam(text: str) -> bytes:
    """
    Synthesize speech using Sarvam Bulbul TTS.
    Best for Hindi and Hinglish — natural Indian voice.

    Args:
        text: Text to synthesize (Hindi, Hinglish, or Romanized)

    Returns:
        Audio bytes (WAV format)
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.sarvam_tts_url,
                headers={
                    "Content-Type": "application/json",
                    "API-Subscription-Key": settings.sarvam_api_key,
                },
                json={
                    "inputs": [text],
                    "target_language_code": "hi-IN",
                    "speaker": settings.sarvam_tts_speaker,
                    "model": settings.sarvam_tts_model,
                    "pitch": 0,
                    "pace": 1.1,  # Slightly slower for empathy
                    "loudness": 1.5,
                    "speech_sample_rate": 22050,
                    "enable_preprocessing": True,
                },
            )

            if response.status_code == 200:
                data = response.json()
                audios = data.get("audios", [])
                if audios:
                    # Sarvam returns base64-encoded audio
                    audio_b64 = audios[0]
                    audio_bytes = base64.b64decode(audio_b64)
                    return audio_bytes

                print("[Sarvam TTS] No audio in response")
                return b""
            else:
                print(f"[Sarvam TTS] API error: {response.status_code} — {response.text}")
                return b""

    except Exception as e:
        print(f"[Sarvam TTS] Error: {e}")
        return b""


# ═══════════════════════════════════════════════════════════
# Auto-Routing TTS
# ═══════════════════════════════════════════════════════════

async def synthesize_auto(text: str, language: str = "en") -> bytes:
    """
    Automatically route text to the best TTS engine based on language.

    Routing:
    - "en" → OpenAI Nova TTS
    - "hi" or "hi-en" → Sarvam Bulbul TTS
    - Unclear → Sarvam Bulbul (safer for Indian users)

    Args:
        text: Text to synthesize
        language: Language code ("en", "hi", "hi-en")

    Returns:
        Audio bytes
    """
    if not text or not text.strip():
        return b""

    # Determine pipeline
    lang = detect_language(text, stt_tag=language)
    pipeline = get_tts_pipeline(lang)

    if pipeline == "openai":
        audio = await synthesize_openai(text)
        # Fallback to Sarvam if OpenAI fails
        if not audio:
            print("[TTS] OpenAI failed, falling back to Sarvam")
            audio = await synthesize_sarvam(text)
        return audio
    else:
        audio = await synthesize_sarvam(text)
        # Fallback to OpenAI if Sarvam fails
        if not audio:
            print("[TTS] Sarvam failed, falling back to OpenAI")
            audio = await synthesize_openai(text)
        return audio
