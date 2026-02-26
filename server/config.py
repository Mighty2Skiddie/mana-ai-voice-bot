"""
Configuration module for AI Voice Bot.
Loads environment variables and defines application constants.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- API Keys ---
    openai_api_key: str = ""
    sarvam_api_key: str = ""
    vapi_api_key: str = ""

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # --- OpenAI Models ---
    llm_model: str = "gpt-4o-mini"
    whisper_model: str = "whisper-1"
    tts_model: str = "tts-1"
    tts_voice: str = "nova"

    # --- Sarvam AI Endpoints ---
    sarvam_stt_url: str = "https://api.sarvam.ai/speech-to-text-translate"
    sarvam_tts_url: str = "https://api.sarvam.ai/text-to-speech"
    sarvam_tts_speaker: str = "anushka"
    sarvam_tts_model: str = "bulbul:v2"

    # --- Latency Targets (ms) ---
    stt_target_ms: int = 400
    safety_target_ms: int = 50
    emotion_target_ms: int = 200
    llm_first_token_target_ms: int = 1200
    tts_target_ms: int = 600
    total_roundtrip_target_ms: int = 2500

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# --- Silence Thresholds ---
SILENCE_THRESHOLDS = {
    5: {
        "en": "Take your time. I'm right here.",
        "hi": "Koi jaldi nahi. Main yahan hoon.",
    },
    10: {
        "en": "No rush at all. We can just sit here.",
        "hi": "Bilkul theek hai. Baat na karein toh bhi.",
    },
    15: {
        "en": "It's okay if you don't want to talk right now.",
        "hi": "Koi baat nahi agar abhi baat nahi karni.",
    },
    20: {
        "en": "Take care. Come back anytime you'd like.",
        "hi": "Apna khayal rakhein. Jab chahein aayein.",
    },
}

# --- Supported Languages ---
SUPPORTED_LANGUAGES = ["en", "hi", "hi-en"]
DEFAULT_LANGUAGE = "hi"  # Default to Sarvam pipeline (safer for Indian users)

# --- Helpline Numbers ---
HELPLINES = {
    "iCall": "9152987821",
    "Vandrevala Foundation": "1860-2662-345",
    "iMind": "040-39246955",
}

# --- Emotion Tags ---
EMOTION_TAGS = ["anxious", "sad", "angry", "frustrated", "neutral", "positive"]

# --- Voice Settings ---
VOICE_SPEED_WPM = 140  # Words per minute — slightly slower than average
MAX_SENTENCES_PER_CHUNK = 2

settings = Settings()
