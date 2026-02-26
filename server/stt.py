"""
Speech-to-Text (STT) Module

Dual-pipeline STT integration:
- English → OpenAI Whisper API
- Hindi / Hinglish → Sarvam Saaras API
"""

import io
import re
import httpx
import base64
from typing import Optional
from openai import AsyncOpenAI
from server.models import STTResponse, Language
from server.config import settings
from server.language_router import detect_language


# ═══════════════════════════════════════════════════════════
# Devanagari → Roman Transliteration (for Hinglish mode)
# ═══════════════════════════════════════════════════════════

_DEVANAGARI_TO_ROMAN = {
    # Vowels
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
    'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'ऋ': 'ri',
    # Vowel signs (matras)
    'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ृ': 'ri',
    # Consonants
    'क': 'ka', 'ख': 'kha', 'ग': 'ga', 'घ': 'gha', 'ङ': 'nga',
    'च': 'cha', 'छ': 'chha', 'ज': 'ja', 'झ': 'jha', 'ञ': 'nya',
    'ट': 'ta', 'ठ': 'tha', 'ड': 'da', 'ढ': 'dha', 'ण': 'na',
    'त': 'ta', 'थ': 'tha', 'द': 'da', 'ध': 'dha', 'न': 'na',
    'प': 'pa', 'फ': 'pha', 'ब': 'ba', 'भ': 'bha', 'म': 'ma',
    'य': 'ya', 'र': 'ra', 'ल': 'la', 'व': 'va', 'श': 'sha',
    'ष': 'sha', 'स': 'sa', 'ह': 'ha',
    # Nukta consonants
    'क़': 'qa', 'ख़': 'kha', 'ग़': 'ga', 'ज़': 'za', 'फ़': 'fa',
    'ड़': 'da', 'ढ़': 'dha',
    # Special
    'ं': 'n', 'ँ': 'n', 'ः': 'h',
    '्': '',  # Halant — suppresses trailing vowel
    'ॉ': 'o',
    # Punctuation
    '।': '.', '॥': '.',
}


def transliterate_devanagari(text: str) -> str:
    """
    Convert Devanagari script to Romanized Hindi (English letters).
    Preserves any English/Latin characters as-is.
    Example: 'मुझे बहुत tension है' → 'mujhe bahut tension hai'
    """
    result = []
    i = 0
    while i < len(text):
        char = text[i]

        # Check for two-char combinations first (nukta consonants)
        if i + 1 < len(text) and text[i:i+2] in _DEVANAGARI_TO_ROMAN:
            result.append(_DEVANAGARI_TO_ROMAN[text[i:i+2]])
            i += 2
            continue

        if char in _DEVANAGARI_TO_ROMAN:
            roman = _DEVANAGARI_TO_ROMAN[char]
            # If this is a matra (vowel sign), replace the trailing 'a' of previous consonant
            if char in 'ािीुूेैोौृॉ' and result:
                # Remove trailing 'a' from last consonant if present
                if result[-1].endswith('a') and len(result[-1]) > 1:
                    result[-1] = result[-1][:-1]
                result.append(roman)
            elif char == '्' and result:
                # Halant: remove trailing 'a' from consonant
                if result[-1].endswith('a') and len(result[-1]) > 1:
                    result[-1] = result[-1][:-1]
            else:
                result.append(roman)
        else:
            # Keep non-Devanagari characters (English, spaces, punctuation) as-is
            result.append(char)
        i += 1

    return ''.join(result)

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

async def transcribe_openai(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    language_hint: str = "en",
) -> STTResponse:
    """
    Transcribe audio using OpenAI Whisper.

    Args:
        audio_bytes: Raw audio data
        filename: Filename hint for the API
        language_hint: ISO language code to tell Whisper what to expect.
                       "en" = English, "hi" = Hindi. MUST be provided.

    Returns:
        STTResponse with transcript and detected language
    """
    try:
        client = _get_openai_client()

        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename

        # ALWAYS tell Whisper the expected language.
        # Without this, Whisper auto-detects poorly (Hindi → Korean, Urdu, etc.)
        response = await client.audio.transcriptions.create(
            model=settings.whisper_model,
            file=audio_file,
            response_format="verbose_json",
            language=language_hint,
        )

        transcript = response.text.strip()
        detected_lang = getattr(response, 'language', language_hint)

        print(f"[OpenAI STT] Transcript: {transcript[:80]} | Hint: {language_hint} | Detected: {detected_lang}")

        # Use the hint language (user's choice) for routing, not Whisper's detection
        language = detect_language(transcript, stt_tag=language_hint)

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

                print(f"[Sarvam STT] Transcript: {transcript[:80]}")

                # Detect if it's pure Hindi or Hinglish
                language = detect_language(transcript, stt_tag="hi")

                return STTResponse(
                    transcript=transcript,
                    language=language,
                    confidence=1.0,
                )
            else:
                print(f"[Sarvam STT] API error: {response.status_code} — {response.text[:200]}")
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

async def transcribe_auto(audio_bytes: bytes, preferred_language: str = "en") -> STTResponse:
    """
    Route audio to the correct STT engine based on user's language selection.

    Strategy:
    - Hindi/Hinglish → Whisper with language="hi" (tells Whisper to expect Hindi)
                       Falls back to Sarvam if Whisper fails.
    - English       → Whisper with language="en"

    Args:
        audio_bytes: Raw audio data
        preferred_language: User's language selection from onboarding ("en", "hi", "hi-en")

    Returns:
        STTResponse with transcript and language tag
    """
    print(f"[STT Auto] User's language selection: {preferred_language}")

    if preferred_language == "hi":
        # Hindi: Tell Whisper to transcribe as Hindi (Devanagari output)
        result = await transcribe_openai(audio_bytes, language_hint="hi")

        if result.transcript:
            result.language = Language.HINDI
            return result

        # Fallback to Sarvam if Whisper returned empty
        print("[STT Auto] Whisper returned empty, trying Sarvam...")
        sarvam_result = await transcribe_sarvam(audio_bytes)
        if sarvam_result.transcript:
            sarvam_result.language = Language.HINDI
            return sarvam_result

        return result

    elif preferred_language == "hi-en":
        # Hinglish: Use Whisper with language="hi" for accurate Hindi recognition,
        # then transliterate Devanagari output → Roman script (English letters)
        result = await transcribe_openai(audio_bytes, language_hint="hi")

        if result.transcript:
            # Convert any Devanagari to Roman letters: 'मुझे tension है' → 'mujhe tension hai'
            result.transcript = transliterate_devanagari(result.transcript)
            result.language = Language.HINGLISH
            print(f"[STT Hinglish] Romanized: {result.transcript[:80]}")
            return result

        return result

    else:
        # English: Tell Whisper to transcribe as English
        return await transcribe_openai(audio_bytes, language_hint="en")
