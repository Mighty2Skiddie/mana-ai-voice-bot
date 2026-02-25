"""
Unit Tests — Conversation Manager
Tests for: session lifecycle, turn tracking, emotion trajectory, silence handling
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.conversation import ConversationManager
from server.models import EmotionTag, Language


class TestSessionLifecycle:
    """Test session creation, retrieval, and cleanup."""

    def test_create_session(self):
        session = ConversationManager.create_session("test-1")
        assert session.session_id == "test-1"
        assert len(session.turns) == 0
        ConversationManager.close_session("test-1")

    def test_create_session_auto_id(self):
        session = ConversationManager.create_session()
        assert session.session_id is not None
        assert len(session.session_id) > 0
        ConversationManager.close_session(session.session_id)

    def test_get_session(self):
        ConversationManager.create_session("test-get")
        session = ConversationManager.get_session("test-get")
        assert session is not None
        assert session.session_id == "test-get"
        ConversationManager.close_session("test-get")

    def test_get_nonexistent_session(self):
        session = ConversationManager.get_session("nonexistent")
        assert session is None

    def test_get_or_create(self):
        session = ConversationManager.get_or_create_session("test-goc")
        assert session.session_id == "test-goc"
        # Get again should return same session
        same = ConversationManager.get_or_create_session("test-goc")
        assert same.session_id == "test-goc"
        ConversationManager.close_session("test-goc")

    def test_close_session(self):
        ConversationManager.create_session("test-close")
        summary = ConversationManager.close_session("test-close")
        assert summary is not None
        # Should not exist anymore
        assert ConversationManager.get_session("test-close") is None

    def test_close_nonexistent(self):
        assert ConversationManager.close_session("nope") is None


class TestTurnTracking:
    """Test conversation turn management."""

    def test_add_user_turn(self):
        ConversationManager.create_session("test-turn")
        session = ConversationManager.add_turn(
            "test-turn", "user", "I'm feeling stressed",
            emotion=EmotionTag.ANXIOUS, language=Language.ENGLISH,
        )
        assert len(session.turns) == 1
        assert session.turns[0].role == "user"
        assert session.turns[0].content == "I'm feeling stressed"
        assert session.current_emotion == EmotionTag.ANXIOUS
        ConversationManager.close_session("test-turn")

    def test_add_assistant_turn(self):
        ConversationManager.create_session("test-asst")
        ConversationManager.add_turn("test-asst", "user", "Help me")
        session = ConversationManager.add_turn("test-asst", "assistant", "I'm here for you")
        assert len(session.turns) == 2
        assert session.turns[1].role == "assistant"
        ConversationManager.close_session("test-asst")

    def test_get_history(self):
        ConversationManager.create_session("test-history")
        ConversationManager.add_turn("test-history", "user", "Hello")
        ConversationManager.add_turn("test-history", "assistant", "Hi there!")
        history = ConversationManager.get_history("test-history")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        ConversationManager.close_session("test-history")

    def test_history_max_turns(self):
        ConversationManager.create_session("test-max")
        for i in range(30):
            ConversationManager.add_turn("test-max", "user", f"Message {i}")
        history = ConversationManager.get_history("test-max", max_turns=5)
        assert len(history) == 5
        ConversationManager.close_session("test-max")


class TestEmotionTracking:
    """Test emotion trajectory tracking."""

    def test_emotion_trajectory(self):
        ConversationManager.create_session("test-emo")
        ConversationManager.add_turn(
            "test-emo", "user", "I'm anxious", emotion=EmotionTag.ANXIOUS
        )
        ConversationManager.add_turn(
            "test-emo", "user", "Feeling better", emotion=EmotionTag.POSITIVE
        )
        trajectory = ConversationManager.get_emotion_trajectory("test-emo")
        assert len(trajectory) == 2
        assert trajectory[0] == EmotionTag.ANXIOUS
        assert trajectory[1] == EmotionTag.POSITIVE
        ConversationManager.close_session("test-emo")

    def test_language_preference_updates(self):
        ConversationManager.create_session("test-lang")
        ConversationManager.add_turn(
            "test-lang", "user", "Hi", language=Language.ENGLISH
        )
        assert ConversationManager.get_language_preference("test-lang") == "en"

        ConversationManager.add_turn(
            "test-lang", "user", "Namaste", language=Language.HINDI
        )
        assert ConversationManager.get_language_preference("test-lang") == "hi"
        ConversationManager.close_session("test-lang")


class TestSilenceHandling:
    """Test silence tier responses."""

    def test_5_second_silence_en(self):
        response = ConversationManager.get_silence_response(5, "en")
        assert response is not None
        assert "here" in response.lower()

    def test_5_second_silence_hi(self):
        response = ConversationManager.get_silence_response(5, "hi")
        assert response is not None
        assert "hoon" in response.lower()

    def test_10_second_silence(self):
        response = ConversationManager.get_silence_response(10, "en")
        assert response is not None

    def test_15_second_silence(self):
        response = ConversationManager.get_silence_response(15, "en")
        assert response is not None

    def test_20_second_silence(self):
        response = ConversationManager.get_silence_response(20, "en")
        assert response is not None
        assert "care" in response.lower() or "come back" in response.lower()

    def test_beyond_20_seconds(self):
        response = ConversationManager.get_silence_response(30, "en")
        assert response is not None  # Should return the 20-second message


class TestContextSummary:
    """Test session context summary generation."""

    def test_new_session_summary(self):
        summary = ConversationManager.get_context_summary("nonexistent")
        assert "no prior context" in summary.lower() or "new session" in summary.lower()

    def test_active_session_summary(self):
        ConversationManager.create_session("test-ctx")
        ConversationManager.add_turn(
            "test-ctx", "user", "I'm stressed",
            emotion=EmotionTag.ANXIOUS, language=Language.ENGLISH,
        )
        summary = ConversationManager.get_context_summary("test-ctx")
        assert "anxious" in summary.lower()
        assert "1 user turn" in summary.lower()
        ConversationManager.close_session("test-ctx")

    def test_crisis_flag_in_summary(self):
        ConversationManager.create_session("test-crisis-ctx")
        ConversationManager.set_crisis_flag("test-crisis-ctx", True)
        summary = ConversationManager.get_context_summary("test-crisis-ctx")
        assert "crisis" in summary.lower()
        ConversationManager.close_session("test-crisis-ctx")
