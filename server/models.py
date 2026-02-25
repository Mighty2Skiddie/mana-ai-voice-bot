"""
Pydantic models for request/response schemas across the AI Voice Bot.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class EmotionTag(str, Enum):
    """Emotion categories detected from user speech."""
    ANXIOUS = "anxious"
    SAD = "sad"
    ANGRY = "angry"
    FRUSTRATED = "frustrated"
    NEUTRAL = "neutral"
    POSITIVE = "positive"


class SafetyLevel(str, Enum):
    """Safety classification levels."""
    SAFE = "safe"
    WARNING = "warning"
    CRISIS = "crisis"


class Language(str, Enum):
    """Supported language codes."""
    ENGLISH = "en"
    HINDI = "hi"
    HINGLISH = "hi-en"


# ═══════════════════════════════════════════════════════════
# Safety Models
# ═══════════════════════════════════════════════════════════

class SafetyResult(BaseModel):
    """Result of safety layer analysis."""
    level: SafetyLevel = SafetyLevel.SAFE
    matched_keywords: List[str] = Field(default_factory=list)
    crisis_response: Optional[str] = None
    helplines: Optional[Dict[str, str]] = None


# ═══════════════════════════════════════════════════════════
# STT / TTS Models
# ═══════════════════════════════════════════════════════════

class STTResponse(BaseModel):
    """Speech-to-Text transcription result."""
    transcript: str
    language: Language = Language.ENGLISH
    confidence: float = 1.0


class TTSRequest(BaseModel):
    """Text-to-Speech synthesis request."""
    text: str
    language: str = "en"


class TTSResponse(BaseModel):
    """TTS response metadata."""
    audio_url: Optional[str] = None
    duration_ms: Optional[int] = None
    language: str = "en"


# ═══════════════════════════════════════════════════════════
# Conversation Models
# ═══════════════════════════════════════════════════════════

class ConversationTurn(BaseModel):
    """A single turn in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    emotion: Optional[EmotionTag] = None
    language: Language = Language.ENGLISH
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionState(BaseModel):
    """Full session state for a conversation."""
    session_id: str
    turns: List[ConversationTurn] = Field(default_factory=list)
    language_preference: Language = Language.ENGLISH
    current_emotion: EmotionTag = EmotionTag.NEUTRAL
    emotion_trajectory: List[EmotionTag] = Field(default_factory=list)
    active_topics: List[str] = Field(default_factory=list)
    is_crisis: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# Chat API Models
# ═══════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    """Direct chat endpoint request."""
    message: str
    session_id: Optional[str] = None
    language: str = "en"


class ChatResponse(BaseModel):
    """Direct chat endpoint response."""
    response: str
    session_id: str
    emotion: str = "neutral"
    language: str = "en"
    is_crisis: bool = False
    safety_response: Optional[str] = None


# ═══════════════════════════════════════════════════════════
# Vapi Webhook Models
# ═══════════════════════════════════════════════════════════

class VapiMessage(BaseModel):
    """Incoming Vapi webhook message."""
    type: str = ""
    call: Optional[Dict[str, Any]] = None
    message: Optional[Dict[str, Any]] = None
    transcript: Optional[str] = None
    language: Optional[str] = None


class VapiAssistantResponse(BaseModel):
    """Response to Vapi assistant-request webhook."""
    assistant: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
