"""
Conversation Manager — Session Memory & Turn Tracking

Manages in-memory conversation state per session including:
- Turn history with emotion and language tags
- Emotion trajectory tracking
- Language preference detection
- Silence tier handling
- Session summarization
"""

import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Optional, List
from server.models import (
    ConversationTurn, SessionState, EmotionTag, Language
)
from server.config import SILENCE_THRESHOLDS


# ═══════════════════════════════════════════════════════════
# In-Memory Session Store
# ═══════════════════════════════════════════════════════════

_sessions: Dict[str, SessionState] = {}


class ConversationManager:
    """
    Manages conversation sessions with full context tracking.
    Stores conversation history, emotion trajectory, and language preferences.
    """

    @staticmethod
    def create_session(session_id: Optional[str] = None) -> SessionState:
        """Create a new conversation session."""
        sid = session_id or str(uuid.uuid4())
        session = SessionState(
            session_id=sid,
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
        )
        _sessions[sid] = session
        return session

    @staticmethod
    def get_session(session_id: str) -> Optional[SessionState]:
        """Retrieve an existing session by ID."""
        return _sessions.get(session_id)

    @staticmethod
    def get_or_create_session(session_id: Optional[str] = None) -> SessionState:
        """Get existing session or create new one."""
        if session_id and session_id in _sessions:
            return _sessions[session_id]
        return ConversationManager.create_session(session_id)

    @staticmethod
    def add_turn(
        session_id: str,
        role: str,
        content: str,
        emotion: EmotionTag = EmotionTag.NEUTRAL,
        language: Language = Language.ENGLISH,
    ) -> SessionState:
        """
        Add a conversation turn to the session.

        Args:
            session_id: The session identifier
            role: "user" or "assistant"
            content: The message content
            emotion: Detected emotion tag
            language: Detected language

        Returns:
            Updated SessionState
        """
        session = ConversationManager.get_or_create_session(session_id)

        turn = ConversationTurn(
            role=role,
            content=content,
            emotion=emotion,
            language=language,
            timestamp=datetime.now(timezone.utc),
        )

        session.turns.append(turn)
        session.last_activity = datetime.now(timezone.utc)

        if role == "user":
            session.current_emotion = emotion
            session.emotion_trajectory.append(emotion)

            # Update language preference based on most recent user input
            session.language_preference = language

        return session

    @staticmethod
    def get_history(session_id: str, max_turns: int = 20) -> List[Dict]:
        """
        Get conversation history formatted for LLM consumption.

        Returns list of {"role": "...", "content": "..."} dicts,
        capped at max_turns for context window management.
        """
        session = _sessions.get(session_id)
        if not session:
            return []

        turns = session.turns[-max_turns:]
        return [
            {"role": turn.role, "content": turn.content}
            for turn in turns
        ]

    @staticmethod
    def get_emotion_trajectory(session_id: str) -> List[EmotionTag]:
        """Get the emotion trajectory for a session."""
        session = _sessions.get(session_id)
        if not session:
            return []
        return session.emotion_trajectory

    @staticmethod
    def get_language_preference(session_id: str) -> str:
        """Get the current language preference for a session."""
        session = _sessions.get(session_id)
        if not session:
            return "en"
        return session.language_preference.value

    @staticmethod
    def set_crisis_flag(session_id: str, is_crisis: bool = True) -> None:
        """Mark a session as having triggered a crisis flag."""
        session = _sessions.get(session_id)
        if session:
            session.is_crisis = is_crisis

    @staticmethod
    def get_context_summary(session_id: str) -> str:
        """
        Generate a context summary for injection into the LLM system prompt.
        Includes emotion trajectory, language preference, and active topics.
        """
        session = _sessions.get(session_id)
        if not session:
            return "New session — no prior context."

        parts = []

        # Turn count
        user_turns = [t for t in session.turns if t.role == "user"]
        parts.append(f"Session has {len(user_turns)} user turns so far.")

        # Language
        parts.append(f"User's current language preference: {session.language_preference.value}")

        # Current emotion
        parts.append(f"User's current detected emotional state: {session.current_emotion.value}")

        # Emotion trajectory
        if len(session.emotion_trajectory) >= 2:
            recent = session.emotion_trajectory[-5:]
            trajectory = " → ".join([e.value for e in recent])
            parts.append(f"Emotion trajectory: {trajectory}")

            # Detect positive shifts
            if recent[-1] in (EmotionTag.POSITIVE, EmotionTag.NEUTRAL) and recent[-2] in (EmotionTag.SAD, EmotionTag.ANXIOUS):
                parts.append("Note: User appears to be feeling better than earlier.")

        # Crisis flag
        if session.is_crisis:
            parts.append("⚠️ CRISIS FLAG: Safety keywords were detected earlier in this session.")

        return " ".join(parts)

    @staticmethod
    def get_silence_response(silence_seconds: int, language: str = "en") -> Optional[str]:
        """
        Get the appropriate silence response based on duration.

        Args:
            silence_seconds: How many seconds of silence
            language: "en" or "hi"

        Returns:
            Appropriate response string or None if no threshold matched
        """
        lang_key = "hi" if language in ("hi", "hi-en") else "en"

        # Find the closest threshold
        for threshold in sorted(SILENCE_THRESHOLDS.keys()):
            if silence_seconds <= threshold:
                return SILENCE_THRESHOLDS[threshold][lang_key]

        # Beyond 20 seconds — session close
        return SILENCE_THRESHOLDS[20][lang_key]

    @staticmethod
    def close_session(session_id: str) -> Optional[str]:
        """
        Close a session and generate a brief summary.

        Returns:
            Session summary string
        """
        session = _sessions.get(session_id)
        if not session:
            return None

        user_turns = [t for t in session.turns if t.role == "user"]
        if not user_turns:
            summary = "Session ended without meaningful interaction."
        else:
            emotions_seen = list(set(e.value for e in session.emotion_trajectory))
            lang = session.language_preference.value
            summary = (
                f"Session with {len(user_turns)} user turns. "
                f"Language: {lang}. "
                f"Emotions observed: {', '.join(emotions_seen)}. "
                f"Crisis flag: {'Yes' if session.is_crisis else 'No'}."
            )

        # Remove from active sessions
        del _sessions[session_id]
        return summary

    @staticmethod
    def get_active_session_count() -> int:
        """Get the number of active sessions."""
        return len(_sessions)

    @staticmethod
    def cleanup_stale_sessions(max_age_minutes: int = 30) -> int:
        """Remove sessions older than max_age_minutes. Returns count removed."""
        now = datetime.now(timezone.utc)
        stale = [
            sid for sid, session in _sessions.items()
            if (now - session.last_activity).total_seconds() > max_age_minutes * 60
        ]
        for sid in stale:
            del _sessions[sid]
        return len(stale)
