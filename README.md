# 🧠 Mana — AI Voice Bot for Mental Health First Conversation Support

> A voice-first AI companion providing empathetic first-line mental health support in **English**, **Hindi**, and **Hinglish** using a hybrid **OpenAI + Sarvam AI** architecture.
Demo - https://mana-ai-voice-bot.onrender.com/
---

## 🌟 Key Features

| Feature | Description |
|---|---|
| **Bilingual Voice Support** | English via OpenAI Nova + Hindi/Hinglish via Sarvam Bulbul |
| **VARA Framework** | Validate → Ask → Reflect → Advance response structure |
| **Crisis Detection** | Hardcoded bilingual keyword scanning with immediate helpline resources |
| **Emotion Intelligence** | Per-turn emotion classification with trajectory tracking |
| **Hinglish Handling** | Natural code-switching detection and response |
| **Privacy-First** | No conversations stored beyond active session |

---

## 🏗️ Architecture

```
User speaks (English / Hindi / Hinglish)
            ↓
    Audio captured by Vapi.ai / Browser
            ↓
    Language Detection (STT tag + text analysis)
      ┌─────┴──────┐
  English        Hindi / Hinglish
      ↓                ↓
 OpenAI Whisper   Sarvam Saaras
    (STT)            (STT)
      └─────┬──────┘
            ↓
   Safety Layer (crisis keyword scan)
            ↓
   Emotion Detection (keyword + LLM)
            ↓
      GPT-4o mini (LLM)
  responds in detected language
            ↓
   Language tag on response
      ┌─────┴──────┐
  English        Hindi / Hinglish
      ↓                ↓
 OpenAI TTS       Sarvam Bulbul
  Nova voice         (TTS)
      └─────┬──────┘
            ↓
   User hears natural voice response
```

---

## 📁 Project Structure

```
├── server/
│   ├── main.py              # FastAPI app + endpoints
│   ├── config.py            # Settings & constants
│   ├── models.py            # Pydantic schemas
│   ├── safety.py            # Crisis keyword detection
│   ├── emotions.py          # Emotion classification
│   ├── conversation.py      # Session & memory manager
│   ├── language_router.py   # Language detection + routing
│   ├── prompts.py           # System prompt + VARA
│   ├── stt.py               # Speech-to-Text (Whisper + Sarvam)
│   └── tts.py               # Text-to-Speech (Nova + Bulbul)
├── frontend/
│   ├── index.html           # Web UI
│   ├── style.css            # Dark-mode premium styling
│   └── script.js            # Chat + voice logic
├── tests/                   # Unit tests
├── .env.example             # API key template
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container deployment
└── railway.json             # Railway config
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
cd "AI Voice Bot — Mental Health First Conversation Support"
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env with your keys:
#   OPENAI_API_KEY=sk-...
#   SARVAM_API_KEY=...
```

### 3. Run the Server

```bash
uvicorn server.main:app --reload --port 8000
```

### 4. Open the App

Navigate to **http://localhost:8000** in your browser.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Text chat (JSON: `{message, session_id, language}`) |
| `POST` | `/tts` | TTS routing (JSON: `{text, language}`) |
| `POST` | `/stt` | STT routing (multipart: audio file + language) |
| `POST` | `/vapi/webhook` | Vapi.ai webhook handler |
| `POST` | `/session/create` | Create new session |
| `GET` | `/session/{id}` | Get session state |
| `POST` | `/session/{id}/close` | Close & summarize session |
| `GET` | `/health` | Health check |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

Tests cover:
- ✅ Crisis keyword detection (English + Hindi) — 33 test cases
- ✅ Emotion classification — 20 test cases
- ✅ Language routing — 18 test cases
- ✅ Conversation management — 22 test cases

---

## 🔧 Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| **LLM** | GPT-4o mini | Empathetic response generation |
| **STT (English)** | OpenAI Whisper | Speech transcription |
| **STT (Hindi)** | Sarvam Saaras | Hindi/Hinglish transcription |
| **TTS (English)** | OpenAI Nova | Natural English voice |
| **TTS (Hindi)** | Sarvam Bulbul | Natural Hindi voice |
| **Backend** | FastAPI + Uvicorn | REST API server |
| **Orchestration** | Vapi.ai | Voice agent platform |
| **Frontend** | Vanilla HTML/CSS/JS | Premium dark-mode UI |

---

## 🆘 Crisis Safety Protocol

The safety layer is **hardcoded and non-overridable**:

1. Every user message is scanned for crisis keywords in **both** English and Hindi
2. Crisis detection **bypasses the LLM entirely**
3. Pre-approved safety scripts provide helpline numbers immediately:
   - **iCall**: 9152987821
   - **Vandrevala Foundation**: 1860-2662-345
   - **iMind**: 040-39246955

---

## 📞 Vapi.ai Integration

1. Deploy the server (Railway, Render, etc.)
2. In Vapi dashboard, set the webhook URL to `https://your-domain.com/vapi/webhook`
3. Set custom TTS webhook to `https://your-domain.com/tts`
4. Generate a shareable demo link

---

## ⚖️ Ethical Limits

- **Never** claims to be a therapist
- **Never** diagnoses mental health conditions
- **Never** recommends medication
- **Never** withholds crisis resources
- **Never** uses manipulative engagement techniques
- **Always** encourages professional help and real-world connections

---

## 📄 License

This project is for educational and demonstration purposes. Not intended for unsupervised clinical use.
