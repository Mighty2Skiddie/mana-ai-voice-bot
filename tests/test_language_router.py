"""
Unit Tests — Language Router
Tests for: English, Hindi, Hinglish, Devanagari, and ambiguous inputs
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.language_router import (
    detect_language, get_tts_pipeline, get_stt_pipeline, get_language_instruction
)
from server.models import Language


class TestLanguageDetection:
    """Test language detection from text and STT tags."""

    # --- STT Tag Priority ---
    def test_stt_tag_english(self):
        assert detect_language("anything", stt_tag="en") == Language.ENGLISH

    def test_stt_tag_hindi(self):
        assert detect_language("anything", stt_tag="hi") == Language.HINDI

    def test_stt_tag_hinglish(self):
        assert detect_language("anything", stt_tag="hi-en") == Language.HINGLISH

    # --- Pure English ---
    def test_pure_english(self):
        assert detect_language("I am feeling stressed about work today") == Language.ENGLISH

    def test_english_greeting(self):
        assert detect_language("Hello, how are you doing?") == Language.ENGLISH

    # --- Pure Hindi (Romanized) ---
    def test_hindi_romanized(self):
        result = detect_language("Main bohot pareshan hoon aaj")
        assert result in (Language.HINDI, Language.HINGLISH)

    def test_hindi_heavy(self):
        result = detect_language("Mujhe koi samajhta nahi hai ghar pe")
        assert result in (Language.HINDI, Language.HINGLISH)

    # --- Devanagari Script ---
    def test_devanagari(self):
        assert detect_language("मुझे बहुत तनाव हो रहा है") == Language.HINDI

    def test_devanagari_mixed(self):
        assert detect_language("मुझे stress हो रहा है") == Language.HINDI

    # --- Hinglish ---
    def test_hinglish_mixed(self):
        result = detect_language("Yaar I'm really stressed aur ghar pe bhi pressure hai")
        assert result == Language.HINGLISH

    def test_hinglish_work_stress(self):
        result = detect_language("Office mein bohot stressed feel ho raha hai")
        assert result in (Language.HINGLISH, Language.HINDI)

    # --- Empty / Edge Cases ---
    def test_empty_string(self):
        assert detect_language("") == Language.ENGLISH

    def test_whitespace(self):
        assert detect_language("   ") == Language.ENGLISH

    def test_single_word_english(self):
        assert detect_language("Hello") == Language.ENGLISH


class TestPipelineRouting:
    """Test TTS/STT pipeline routing."""

    def test_tts_english_uses_openai(self):
        assert get_tts_pipeline(Language.ENGLISH) == "openai"

    def test_tts_hindi_uses_sarvam(self):
        assert get_tts_pipeline(Language.HINDI) == "sarvam"

    def test_tts_hinglish_uses_sarvam(self):
        assert get_tts_pipeline(Language.HINGLISH) == "sarvam"

    def test_stt_english_uses_openai(self):
        assert get_stt_pipeline(Language.ENGLISH) == "openai"

    def test_stt_hindi_uses_sarvam(self):
        assert get_stt_pipeline(Language.HINDI) == "sarvam"

    def test_stt_hinglish_uses_sarvam(self):
        assert get_stt_pipeline(Language.HINGLISH) == "sarvam"


class TestLanguageInstructions:
    """Test language instruction generation for LLM."""

    def test_english_instruction(self):
        instruction = get_language_instruction(Language.ENGLISH)
        assert "English" in instruction

    def test_hindi_instruction(self):
        instruction = get_language_instruction(Language.HINDI)
        assert "Hindi" in instruction

    def test_hinglish_instruction(self):
        instruction = get_language_instruction(Language.HINGLISH)
        assert "Hinglish" in instruction or "mix" in instruction.lower()
