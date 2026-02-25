"""
AI Voice Bot — Mental Health First Conversation Support
Main FastAPI Application

Endpoints:
  - POST /vapi/webhook    → Vapi.ai webhook handler
  - POST /tts             → TTS routing endpoint (OpenAI Nova / Sarvam Bulbul)
  - POST /stt             → STT routing endpoint (Whisper / Sarvam Saaras)
  - POST /chat            → Direct text chat endpoint (for frontend testing)
  - GET  /health          → Health check
  - GET  /                → Serves frontend
"""

import os
import uuid
import time
import base64
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from server.config import settings
from server.models import (
    TTSRequest, ChatRequest, ChatResponse,
    SafetyLevel, Language, VapiMessage,
)
from server.safety import check_safety
from server.emotions import detect_emotion, detect_emotion_sync, get_emotion_trajectory_summary
from server.conversation import ConversationManager
from server.language_router import detect_language, get_language_instruction, get_tts_pipeline
from server.prompts import get_system_prompt, get_opening_script, get_crisis_override
from server.tts import synthesize_auto, synthesize_openai, synthesize_sarvam
from server.stt import transcribe_auto


# ═══════════════════════════════════════════════════════════
# App Lifecycle
# ═══════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    print("=" * 60)
    print("  🧠 Mana — AI Voice Bot for Mental Health Support")
    print("  🌐 Hybrid Architecture: OpenAI + Sarvam AI")
    print(f"  🔑 OpenAI Key: {'✓ configured' if settings.openai_api_key else '✗ missing'}")
    print(f"  🔑 Sarvam Key: {'✓ configured' if settings.sarvam_api_key else '✗ missing'}")
    print(f"  📡 Server: http://{settings.host}:{settings.port}")
    print("=" * 60)
    yield
    # Cleanup stale sessions on shutdown
    cleaned = ConversationManager.cleanup_stale_sessions(max_age_minutes=0)
    print(f"Shutdown: cleaned {cleaned} active sessions")


# ═══════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="Mana — AI Voice Bot",
    description="Mental Health First Conversation Support",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LLM client
_llm_client: Optional[AsyncOpenAI] = None


def _get_llm_client() -> AsyncOpenAI:
    global _llm_client
    if _llm_client is None:
        _llm_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _llm_client


# ═══════════════════════════════════════════════════════════
# Core Processing Pipeline
# ═══════════════════════════════════════════════════════════

async def process_message(
    text: str,
    session_id: str,
    language_hint: str = "en",
) -> dict:
    """
    The core 7-layer processing pipeline:
    1. Language Detection
    2. Safety Check (crisis keyword scan)
    3. Emotion Detection
    4. Session Context Building
    5. LLM Response Generation
    6. Response Language Tagging
    7. Ready for TTS routing

    Returns:
        dict with: response, language, emotion, is_crisis, safety_response
    """
    start_time = time.time()

    # Layer 1: Language Detection
    language = detect_language(text, stt_tag=language_hint)
    lang_code = language.value

    # Layer 2: Safety Check — BEFORE anything else
    safety = check_safety(text, language=lang_code)

    if safety.level == SafetyLevel.CRISIS:
        # CRISIS: Bypass LLM entirely, play safety script
        ConversationManager.set_crisis_flag(session_id, True)
        ConversationManager.add_turn(
            session_id, "user", text,
            emotion=detect_emotion_sync(text),
            language=language,
        )
        crisis_response = get_crisis_override(lang_code)
        ConversationManager.add_turn(
            session_id, "assistant", crisis_response,
            language=language,
        )
        return {
            "response": crisis_response,
            "language": lang_code,
            "emotion": "crisis",
            "is_crisis": True,
            "safety_response": crisis_response,
            "latency_ms": int((time.time() - start_time) * 1000),
        }

    # Layer 3: Emotion Detection (keyword-based for speed, async for accuracy)
    emotion_quick = detect_emotion_sync(text)

    # Layer 4: Update Conversation Manager
    session = ConversationManager.get_or_create_session(session_id)
    ConversationManager.add_turn(
        session_id, "user", text,
        emotion=emotion_quick,
        language=language,
    )

    # Layer 5: Build Context + Generate LLM Response
    context_summary = ConversationManager.get_context_summary(session_id)
    history = ConversationManager.get_history(session_id, max_turns=20)
    system_prompt = get_system_prompt(language=lang_code, context_summary=context_summary)

    # Check if this is the first turn — include opening
    if len([t for t in session.turns if t.role == "user"]) == 1:
        # First user message — prepend opening to assistant context
        opening = get_opening_script(lang_code)
        history = [{"role": "assistant", "content": opening}] + history

    # Build messages for LLM
    messages = [{"role": "system", "content": system_prompt}] + history

    # Add language instruction to ensure correct language response
    lang_instruction = get_language_instruction(language)
    messages.append({
        "role": "system",
        "content": f"Language instruction for this turn: {lang_instruction}"
    })

    # Handle WARNING-level safety
    if safety.level == SafetyLevel.WARNING:
        messages.append({
            "role": "system",
            "content": (
                "IMPORTANT: The user's message contains concerning language. "
                "While not an immediate crisis, naturally weave in awareness of helpline resources "
                "and show extra care. Do NOT alarm the user or label their feelings explicitly."
            )
        })

    try:
        client = _get_llm_client()
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            max_tokens=300,
            temperature=0.7,
            top_p=0.9,
        )

        assistant_response = response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[LLM] Error: {e}")
        # Graceful fallback
        if lang_code in ("hi", "hi-en"):
            assistant_response = "Main sun raha hoon. Kya aap thoda aur bata sakte hain?"
        else:
            assistant_response = "I hear you. Would you like to tell me a bit more?"

    # Layer 6: Store assistant response
    ConversationManager.add_turn(
        session_id, "assistant", assistant_response,
        language=language,
    )

    latency_ms = int((time.time() - start_time) * 1000)
    print(f"[Pipeline] Processed in {latency_ms}ms | Lang: {lang_code} | Emotion: {emotion_quick.value}")

    return {
        "response": assistant_response,
        "language": lang_code,
        "emotion": emotion_quick.value,
        "is_crisis": False,
        "safety_response": safety.crisis_response if safety.level == SafetyLevel.WARNING else None,
        "latency_ms": latency_ms,
    }


# ═══════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "bot": "Mana — AI Voice Bot",
        "active_sessions": ConversationManager.get_active_session_count(),
        "openai_configured": bool(settings.openai_api_key),
        "sarvam_configured": bool(settings.sarvam_api_key),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Direct text chat endpoint for frontend testing.
    No audio — pure text in, text out.
    """
    session_id = request.session_id or str(uuid.uuid4())

    result = await process_message(
        text=request.message,
        session_id=session_id,
        language_hint=request.language,
    )

    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        emotion=result["emotion"],
        language=result["language"],
        is_crisis=result["is_crisis"],
        safety_response=result.get("safety_response"),
    )


@app.post("/tts")
async def tts_endpoint(request: TTSRequest):
    """
    TTS routing endpoint.
    Routes to OpenAI Nova (English) or Sarvam Bulbul (Hindi/Hinglish).

    Used by Vapi.ai as a custom TTS webhook.
    """
    audio_bytes = await synthesize_auto(
        text=request.text,
        language=request.language,
    )

    if not audio_bytes:
        raise HTTPException(status_code=500, detail="TTS synthesis failed")

    # Determine content type
    content_type = "audio/mpeg"  # MP3 for OpenAI
    if request.language in ("hi", "hi-en"):
        content_type = "audio/wav"  # WAV for Sarvam

    return Response(
        content=audio_bytes,
        media_type=content_type,
        headers={"Content-Disposition": "inline; filename=response.mp3"},
    )


@app.post("/stt")
async def stt_endpoint(
    audio: UploadFile = File(...),
    language: str = Form("en"),
):
    """
    STT routing endpoint.
    Routes to OpenAI Whisper (English) or Sarvam Saaras (Hindi/Hinglish).
    """
    audio_bytes = await audio.read()

    result = await transcribe_auto(
        audio_bytes=audio_bytes,
        preferred_language=language,
    )

    return {
        "transcript": result.transcript,
        "language": result.language.value,
        "confidence": result.confidence,
    }


# ═══════════════════════════════════════════════════════════
# Vapi.ai Webhook Handler
# ═══════════════════════════════════════════════════════════

@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    """
    Main Vapi.ai webhook handler.
    Handles different Vapi message types:
    - assistant-request: Provide assistant configuration
    - function-call: Handle tool calls
    - transcript: Process user speech
    - end-of-call-report: Session cleanup
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    message_type = body.get("message", {}).get("type", body.get("type", ""))

    # --- Assistant Request ---
    if message_type == "assistant-request":
        return JSONResponse({
            "assistant": {
                "model": {
                    "provider": "openai",
                    "model": settings.llm_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": get_system_prompt(),
                        }
                    ],
                    "temperature": 0.7,
                    "maxTokens": 300,
                },
                "voice": {
                    "provider": "openai",
                    "voiceId": settings.tts_voice,
                },
                "firstMessage": get_opening_script("en"),
                "name": "Mana",
            }
        })

    # --- Conversation Update (transcript received) ---
    if message_type in ("conversation-update", "transcript"):
        transcript = body.get("message", {}).get("transcript", "")
        call_id = body.get("message", {}).get("call", {}).get("id", str(uuid.uuid4()))

        if transcript:
            # Run through our pipeline
            result = await process_message(
                text=transcript,
                session_id=call_id,
                language_hint="en",
            )

            return JSONResponse({
                "response": result["response"],
                "language": result["language"],
                "emotion": result["emotion"],
            })

    # --- End of Call ---
    if message_type == "end-of-call-report":
        call_id = body.get("message", {}).get("call", {}).get("id", "")
        if call_id:
            summary = ConversationManager.close_session(call_id)
            print(f"[Vapi] Call ended: {call_id} — {summary}")

        return JSONResponse({"status": "ok"})

    # --- Status Update ---
    if message_type == "status-update":
        return JSONResponse({"status": "ok"})

    # Default response
    return JSONResponse({"status": "ok"})


# ═══════════════════════════════════════════════════════════
# Session Management Endpoints
# ═══════════════════════════════════════════════════════════

@app.post("/session/create")
async def create_session():
    """Create a new conversation session."""
    session = ConversationManager.create_session()
    return {
        "session_id": session.session_id,
        "message": "Session created",
    }


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session state."""
    session = ConversationManager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "turns": len(session.turns),
        "language": session.language_preference.value,
        "emotion": session.current_emotion.value,
        "is_crisis": session.is_crisis,
    }


@app.post("/session/{session_id}/close")
async def close_session(session_id: str):
    """Close a session and get summary."""
    summary = ConversationManager.close_session(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"summary": summary}


# ═══════════════════════════════════════════════════════════
# Serve Frontend
# ═══════════════════════════════════════════════════════════

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

# Mount static files if frontend directory exists
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main frontend page."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Mana — AI Voice Bot</h1><p>Frontend not found.</p>")


# ═══════════════════════════════════════════════════════════
# Run Server
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
