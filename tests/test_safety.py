"""
Unit Tests — Safety Layer (Crisis Keyword Detection)
Tests for: English crisis keywords, Hindi crisis keywords, safe inputs, warning detection
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.safety import check_safety
from server.models import SafetyLevel


class TestCrisisDetectionEnglish:
    """Test crisis keyword detection in English."""

    def test_direct_suicide_mention(self):
        result = check_safety("I want to kill myself", "en")
        assert result.level == SafetyLevel.CRISIS
        assert len(result.matched_keywords) > 0
        assert result.crisis_response is not None

    def test_want_to_die(self):
        result = check_safety("I just want to die", "en")
        assert result.level == SafetyLevel.CRISIS

    def test_self_harm(self):
        result = check_safety("I've been hurting myself lately", "en")
        assert result.level == SafetyLevel.CRISIS

    def test_end_my_life(self):
        result = check_safety("I want to end my life", "en")
        assert result.level == SafetyLevel.CRISIS

    def test_suicide_word(self):
        result = check_safety("I'm feeling suicidal", "en")
        assert result.level == SafetyLevel.CRISIS

    def test_passive_death_wish(self):
        result = check_safety("I hope I don't wake up tomorrow", "en")
        assert result.level == SafetyLevel.CRISIS

    def test_planning_indicators(self):
        result = check_safety("I've already written a note for everyone", "en")
        assert result.level == SafetyLevel.CRISIS

    def test_no_reason_to_live(self):
        result = check_safety("There's no reason to live anymore", "en")
        assert result.level == SafetyLevel.CRISIS

    def test_helplines_provided(self):
        result = check_safety("I want to end it all", "en")
        assert result.level == SafetyLevel.CRISIS
        assert result.helplines is not None
        assert "iCall" in result.helplines
        assert "Vandrevala Foundation" in result.helplines

    def test_crisis_response_in_english(self):
        result = check_safety("I want to kill myself", "en")
        assert "iCall" in result.crisis_response
        assert "9152987821" in result.crisis_response


class TestCrisisDetectionHindi:
    """Test crisis keyword detection in Hindi."""

    def test_khudkushi(self):
        result = check_safety("Main khudkushi karna chahta hoon", "hi")
        assert result.level == SafetyLevel.CRISIS

    def test_mar_jaana(self):
        result = check_safety("Main mar jaana chahta hoon", "hi")
        assert result.level == SafetyLevel.CRISIS

    def test_jeena_nahi_chahta(self):
        result = check_safety("Mujhe jeena nahi chahta", "hi")
        assert result.level == SafetyLevel.CRISIS

    def test_sab_khatam(self):
        result = check_safety("Main sab khatam karna hai", "hi")
        assert result.level == SafetyLevel.CRISIS

    def test_khud_ko_hurt(self):
        result = check_safety("Main khud ko hurt karna chahta hoon", "hi")
        assert result.level == SafetyLevel.CRISIS

    def test_life_end_karna(self):
        result = check_safety("Mujhe apni life end karna hai", "hi")
        assert result.level == SafetyLevel.CRISIS

    def test_crisis_response_in_hindi(self):
        result = check_safety("Main mar jaana chahta hoon", "hi")
        assert "iCall" in result.crisis_response
        assert "aapke saath" in result.crisis_response.lower() or "madad" in result.crisis_response.lower()


class TestWarningDetection:
    """Test warning-level keyword detection."""

    def test_cant_take_it(self):
        result = check_safety("I can't take it anymore", "en")
        assert result.level == SafetyLevel.WARNING

    def test_tired_of_living(self):
        result = check_safety("I'm tired of living like this", "en")
        assert result.level == SafetyLevel.WARNING

    def test_nobody_cares_en(self):
        result = check_safety("Nobody cares about me anyway", "en")
        assert result.level == SafetyLevel.WARNING

    def test_hindi_warning(self):
        result = check_safety("Thak gaya hoon sab se", "hi")
        assert result.level == SafetyLevel.WARNING

    def test_sab_bekar(self):
        result = check_safety("Sab bekar hai yaar", "hi")
        assert result.level == SafetyLevel.WARNING

    def test_warning_includes_helplines(self):
        result = check_safety("I can't take it anymore", "en")
        assert result.helplines is not None


class TestSafeInputs:
    """Test that safe inputs are correctly classified."""

    def test_normal_greeting(self):
        result = check_safety("Hi, how are you?", "en")
        assert result.level == SafetyLevel.SAFE
        assert len(result.matched_keywords) == 0

    def test_work_stress(self):
        result = check_safety("I'm really stressed about work", "en")
        assert result.level == SafetyLevel.SAFE

    def test_relationship_issue(self):
        result = check_safety("My girlfriend and I had a fight", "en")
        assert result.level == SafetyLevel.SAFE

    def test_hindi_normal(self):
        result = check_safety("Aaj bohot thaka hua hoon", "hi")
        assert result.level == SafetyLevel.SAFE

    def test_empty_input(self):
        result = check_safety("", "en")
        assert result.level == SafetyLevel.SAFE

    def test_whitespace_only(self):
        result = check_safety("   ", "en")
        assert result.level == SafetyLevel.SAFE

    def test_feeling_sad(self):
        """Sadness alone should NOT trigger crisis."""
        result = check_safety("I'm feeling really sad today", "en")
        assert result.level == SafetyLevel.SAFE

    def test_anxiety(self):
        result = check_safety("I have so much anxiety about the presentation", "en")
        assert result.level == SafetyLevel.SAFE


class TestCrossLanguageDetection:
    """Test that crisis keywords are detected regardless of language parameter."""

    def test_english_crisis_with_hindi_param(self):
        """English crisis should be detected even if language is set to Hindi."""
        result = check_safety("I want to kill myself", "hi")
        assert result.level == SafetyLevel.CRISIS

    def test_hindi_crisis_with_english_param(self):
        """Hindi crisis should be detected even if language is set to English."""
        result = check_safety("Main khudkushi karna chahta hoon", "en")
        assert result.level == SafetyLevel.CRISIS
