"""
Language Detection + Routing Logic

Detects user language from STT tags or text analysis and routes
to the appropriate STT/TTS pipeline:
  - English → OpenAI Whisper / OpenAI Nova TTS
  - Hindi / Hinglish → Sarvam Saaras / Sarvam Bulbul TTS
  - Unclear → Default to Sarvam pipeline (safer for Indian users)
"""

import re
from typing import Tuple
from server.models import Language


# ═══════════════════════════════════════════════════════════
# Hindi / Devanagari Detection Patterns
# ═══════════════════════════════════════════════════════════

# Devanagari Unicode range
DEVANAGARI_PATTERN = re.compile(r'[\u0900-\u097F]')

# Common Hindi romanized words (top 100 most frequent)
HINDI_ROMANIZED_WORDS = {
    "hai", "hain", "ho", "hoon", "nahi", "nahin", "nhi",
    "kya", "kaise", "kaisa", "kaisi", "kyun", "kyu", "kyunki",
    "mein", "main", "mera", "meri", "mere", "humara",
    "tum", "tumhara", "tumhari", "aap", "aapka", "aapki",
    "woh", "yeh", "ye", "isko", "usko",
    "aur", "par", "lekin", "phir", "toh", "bhi",
    "bohot", "bahut", "bahot", "zyada", "thoda", "kam",
    "achha", "achhi", "bura", "buri", "theek",
    "karna", "karte", "karti", "karta", "kar",
    "hona", "hota", "hoti", "hua", "hui",
    "jaana", "jata", "jati", "gaya", "gayi", "jao",
    "aana", "aata", "aati", "aaya", "aayi", "aao",
    "bolna", "bolta", "bolti", "bolo", "bol",
    "sunna", "sunta", "sunti", "suno", "sun",
    "dekhna", "dekhta", "dekhti", "dekho", "dekh",
    "samajhna", "samajhta", "samajhti", "samjho",
    "abhi", "ab", "tab", "jab", "kabhi", "hamesha",
    "ghar", "kaam", "log", "dost", "yaar",
    "mann", "dil", "zindagi", "duniya",
    "please", "matlab", "wala", "wali", "chahta", "chahti",
    "chahiye", "sakta", "sakti", "raha", "rahi",
    "bilkul", "sach", "jhooth", "pata", "maloom",
    "paisa", "time", "jagah", "baat", "sawaal",
    "lagta", "lagti", "laga", "lagi",
    "rehta", "rehti", "reh", "rehna",
    "milta", "milti", "mila", "mili",
}

# Common Hinglish patterns (mixing signals)
HINGLISH_PATTERNS = [
    r'\b(yaar|bhai|dude)\b.*\b(is|am|was|the|but|and)\b',
    r'\b(is|am|was|the|but|and)\b.*\b(yaar|bhai|hai|nahi)\b',
    r'\b(feel|stressed|anxiety|work)\b.*\b(hai|hoon|raha|rahi)\b',
    r'\b(bohot|bahut|kuch)\b.*\b(stressed|tired|done|busy)\b',
]


# ═══════════════════════════════════════════════════════════
# Language Detection Functions
# ═══════════════════════════════════════════════════════════

def _has_devanagari(text: str) -> bool:
    """Check if text contains Devanagari script characters."""
    return bool(DEVANAGARI_PATTERN.search(text))


def _count_hindi_words(text: str) -> int:
    """Count the number of recognized Hindi romanized words in text."""
    words = text.lower().split()
    return sum(1 for w in words if w.strip(".,!?;:'\"") in HINDI_ROMANIZED_WORDS)


def _is_hinglish(text: str) -> bool:
    """Detect Hinglish (mixed Hindi + English) patterns."""
    text_lower = text.lower()
    for pattern in HINGLISH_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def detect_language(text: str, stt_tag: str = "") -> Language:
    """
    Detect the language of user input.

    Priority:
    1. STT language tag (if provided by Whisper or Sarvam)
    2. Devanagari script detection → Hindi
    3. Hinglish pattern matching → Hinglish
    4. Hindi romanized word ratio analysis
    5. Default: Sarvam pipeline (safer for Indian users)

    Args:
        text: The transcribed text
        stt_tag: Language tag from STT engine ("en", "hi", "hi-en", etc.)

    Returns:
        Language enum value
    """
    # 1. Trust STT tag if provided
    if stt_tag:
        stt_tag_lower = stt_tag.lower().strip()
        if stt_tag_lower in ("en", "english"):
            return Language.ENGLISH
        elif stt_tag_lower in ("hi", "hindi"):
            return Language.HINDI
        elif stt_tag_lower in ("hi-en", "hinglish", "hi-eng"):
            return Language.HINGLISH

    if not text or not text.strip():
        return Language.ENGLISH

    # 2. Devanagari script → Hindi
    if _has_devanagari(text):
        return Language.HINDI

    # 3. Check for Hinglish mixing
    if _is_hinglish(text):
        return Language.HINGLISH

    # 4. Hindi romanized word ratio
    words = text.lower().split()
    total_words = len(words)
    if total_words > 0:
        hindi_count = _count_hindi_words(text)
        hindi_ratio = hindi_count / total_words

        if hindi_ratio > 0.5:
            return Language.HINDI
        elif hindi_ratio > 0.2:
            return Language.HINGLISH

    # 5. Default to English
    return Language.ENGLISH


def get_tts_pipeline(language: Language) -> str:
    """
    Determine which TTS pipeline to use based on language.

    Returns:
        "openai" for English, "sarvam" for Hindi/Hinglish
    """
    if language == Language.ENGLISH:
        return "openai"
    return "sarvam"


def get_stt_pipeline(language: Language) -> str:
    """
    Determine which STT pipeline to use based on language.

    Returns:
        "openai" for English, "sarvam" for Hindi/Hinglish
    """
    if language == Language.ENGLISH:
        return "openai"
    return "sarvam"


def get_language_instruction(language: Language) -> str:
    """
    Get language instruction to inject into LLM system prompt.
    Ensures the model responds in the correct language.
    """
    if language == Language.ENGLISH:
        return "Respond in English. Use warm, conversational English with natural contractions."
    elif language == Language.HINDI:
        return (
            "Respond in Hindi (Romanized/Hinglish script). "
            "Use natural Hindi as spoken by young adults in India. "
            "Example: 'Main samajh sakta hoon, yeh bohot mushkil hai.'"
        )
    else:  # HINGLISH
        return (
            "Respond in Hinglish — a natural mix of Hindi and English as spoken by young Indians. "
            "Mirror the user's mixing style. "
            "Example: 'Yaar I understand, yeh sach mein bohot heavy hai.'"
        )
