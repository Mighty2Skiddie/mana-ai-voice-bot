"""
Unit Tests — Emotion Detection (Keyword-based fallback)
Tests for: all emotion categories in English and Hindi
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.emotions import detect_emotion_sync, get_emotion_trajectory_summary
from server.models import EmotionTag


class TestEmotionDetectionEnglish:
    """Test keyword-based emotion detection in English."""

    def test_anxious_worried(self):
        assert detect_emotion_sync("I'm so worried about tomorrow") == EmotionTag.ANXIOUS

    def test_anxious_overthinking(self):
        assert detect_emotion_sync("I can't stop overthinking everything") == EmotionTag.ANXIOUS

    def test_anxious_panic(self):
        assert detect_emotion_sync("I'm having a panic attack") == EmotionTag.ANXIOUS

    def test_sad_lonely(self):
        assert detect_emotion_sync("I feel so lonely these days") == EmotionTag.SAD

    def test_sad_depressed(self):
        assert detect_emotion_sync("I've been feeling depressed lately") == EmotionTag.SAD

    def test_sad_crying(self):
        assert detect_emotion_sync("I was crying all night") == EmotionTag.SAD

    def test_angry(self):
        assert detect_emotion_sync("I'm so angry at everyone") == EmotionTag.ANGRY

    def test_angry_hate(self):
        assert detect_emotion_sync("I hate my job so much") == EmotionTag.ANGRY

    def test_frustrated(self):
        assert detect_emotion_sync("I'm so frustrated, nothing works") == EmotionTag.FRUSTRATED

    def test_frustrated_stuck(self):
        assert detect_emotion_sync("I feel stuck in this situation") == EmotionTag.FRUSTRATED

    def test_positive(self):
        assert detect_emotion_sync("I'm feeling a bit better today") == EmotionTag.POSITIVE

    def test_positive_grateful(self):
        assert detect_emotion_sync("I'm grateful for this talk") == EmotionTag.POSITIVE

    def test_neutral(self):
        assert detect_emotion_sync("Just checking in with you") == EmotionTag.NEUTRAL

    def test_neutral_empty(self):
        assert detect_emotion_sync("") == EmotionTag.NEUTRAL

    def test_neutral_none(self):
        assert detect_emotion_sync(None) == EmotionTag.NEUTRAL


class TestEmotionDetectionHindi:
    """Test keyword-based emotion detection in Hindi/Hinglish."""

    def test_anxious_tension(self):
        assert detect_emotion_sync("Bohot tension ho rahi hai") == EmotionTag.ANXIOUS

    def test_anxious_dar(self):
        assert detect_emotion_sync("Mujhe dar lag raha hai") == EmotionTag.ANXIOUS

    def test_sad_udaas(self):
        assert detect_emotion_sync("Main bohot udaas hoon") == EmotionTag.SAD

    def test_sad_akela(self):
        assert detect_emotion_sync("Main akela feel kar raha hoon") == EmotionTag.SAD

    def test_angry_gussa(self):
        assert detect_emotion_sync("Mujhe bohot gussa aa raha hai") == EmotionTag.ANGRY

    def test_frustrated_thak_gaya(self):
        assert detect_emotion_sync("Main thak gaya hoon sab se") == EmotionTag.FRUSTRATED

    def test_positive_achha(self):
        assert detect_emotion_sync("Ab achha lag raha hai") == EmotionTag.POSITIVE

    def test_positive_behtar(self):
        assert detect_emotion_sync("Ab behtar feel ho raha hai") == EmotionTag.POSITIVE


class TestEmotionTrajectory:
    """Test emotion trajectory summarization."""

    def test_empty_trajectory(self):
        summary = get_emotion_trajectory_summary([])
        assert "No emotional trajectory" in summary

    def test_single_emotion(self):
        summary = get_emotion_trajectory_summary([EmotionTag.ANXIOUS])
        assert "anxious" in summary.lower()

    def test_positive_shift(self):
        trajectory = [EmotionTag.SAD, EmotionTag.NEUTRAL, EmotionTag.POSITIVE]
        summary = get_emotion_trajectory_summary(trajectory)
        assert "better" in summary.lower() or "positive" in summary.lower()

    def test_stabilizing(self):
        trajectory = [EmotionTag.ANXIOUS, EmotionTag.NEUTRAL]
        summary = get_emotion_trajectory_summary(trajectory)
        assert "stabilizing" in summary.lower() or "trajectory" in summary.lower()

    def test_persistent_distress(self):
        trajectory = [EmotionTag.SAD, EmotionTag.ANXIOUS, EmotionTag.SAD]
        summary = get_emotion_trajectory_summary(trajectory)
        assert "distressed" in summary.lower() or "trajectory" in summary.lower()
