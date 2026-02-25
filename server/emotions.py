"""
Emotion Detection Module

Classifies user transcript into emotion categories using GPT-4o mini.
Tracks emotion trajectory across conversation turns.
Emotions: Anxious, Sad, Angry, Frustrated, Neutral, Positive
"""

from typing import Optional, List
from openai import AsyncOpenAI
from server.models import EmotionTag
from server.config import settings

# Initialize OpenAI client
_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    """Lazy-initialize the OpenAI client."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


# ═══════════════════════════════════════════════════════════
# Emotion Classification Prompt
# ═══════════════════════════════════════════════════════════

EMOTION_CLASSIFICATION_PROMPT = """You are an emotion classifier for a mental health support chatbot.
Classify the user's message into EXACTLY ONE of these categories:
- anxious (worry, nervousness, overthinking, panic, fear of future)
- sad (sadness, grief, loneliness, hopelessness, feeling low)
- angry (anger, frustration directed outward, irritation, resentment)
- frustrated (feeling stuck, helpless, overwhelmed, burnout)
- neutral (calm, matter-of-fact, no strong emotion detected)
- positive (hopeful, relieved, grateful, happy, feeling better)

Rules:
1. Respond with ONLY the emotion label, nothing else
2. If the message is in Hindi or Hinglish, classify the emotion the same way
3. If unclear, default to "neutral"
4. Focus on the DOMINANT emotion if multiple are present

Examples:
"I can't stop thinking about work" → anxious
"Kuch nahi hoga mera" → sad
"I'm so sick of everyone telling me what to do" → angry
"I'm stuck and nothing is working" → frustrated
"Just checking in" → neutral
"I feel a little better after talking" → positive
"Bohot tension ho rahi hai" → anxious
"Thak gaya hoon sab se" → sad"""


# ═══════════════════════════════════════════════════════════
# Emotion Detection
# ═══════════════════════════════════════════════════════════

async def detect_emotion(text: str) -> EmotionTag:
    """
    Classify the emotional tone of user text using GPT-4o mini.

    Args:
        text: User's transcribed message (English, Hindi, or Hinglish)

    Returns:
        EmotionTag enum value
    """
    if not text or not text.strip():
        return EmotionTag.NEUTRAL

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": EMOTION_CLASSIFICATION_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=10,
            temperature=0.0,
        )

        result = response.choices[0].message.content.strip().lower()

        # Map to EmotionTag
        emotion_map = {
            "anxious": EmotionTag.ANXIOUS,
            "sad": EmotionTag.SAD,
            "angry": EmotionTag.ANGRY,
            "frustrated": EmotionTag.FRUSTRATED,
            "neutral": EmotionTag.NEUTRAL,
            "positive": EmotionTag.POSITIVE,
        }

        return emotion_map.get(result, EmotionTag.NEUTRAL)

    except Exception as e:
        print(f"[Emotion Detection] Error: {e}")
        return EmotionTag.NEUTRAL


def detect_emotion_sync(text: str) -> EmotionTag:
    """
    Lightweight keyword-based emotion detection (no API call).
    Used as fallback when API is unavailable or for quick checks.
    """
    if not text:
        return EmotionTag.NEUTRAL

    text_lower = text.lower()

    # Anxious indicators (EN + HI)
    anxious_words = [
        "worried", "anxious", "nervous", "panic", "overthinking", "can't stop thinking",
        "scared", "afraid", "tension", "dar", "ghabra", "chinta", "soch", "thinking too much",
        "bohot tension", "dar lag raha", "ghabrahat",
    ]

    # Sad indicators (EN + HI)
    sad_words = [
        "sad", "lonely", "alone", "crying", "depressed", "hopeless", "empty", "lost",
        "miss", "grief", "dukhi", "udaas", "akela", "rona", "aansu", "kuch nahi hoga",
        "bohot bura", "mann nahi", "tanha",
    ]

    # Angry indicators (EN + HI)
    angry_words = [
        "angry", "furious", "hate", "sick of", "fed up", "pissed",
        "gussa", "nafrat", "tang aa gaya", "bardasht nahi", "chid",
    ]

    # Frustrated indicators (EN + HI)
    frustrated_words = [
        "stuck", "overwhelmed", "can't do this", "nothing works", "frustrated",
        "burnout", "exhausted", "giving up",
        "thak gaya", "kuch nahi ho raha", "haar", "majboor", "pareshan",
    ]

    # Positive indicators (EN + HI)
    positive_words = [
        "better", "good", "happy", "hopeful", "grateful", "thank",
        "relieved", "calm", "peaceful",
        "achha", "behtar", "khushi", "shukriya", "theek", "achha lag raha",
    ]

    for word in anxious_words:
        if word in text_lower:
            return EmotionTag.ANXIOUS

    for word in sad_words:
        if word in text_lower:
            return EmotionTag.SAD

    for word in angry_words:
        if word in text_lower:
            return EmotionTag.ANGRY

    for word in frustrated_words:
        if word in text_lower:
            return EmotionTag.FRUSTRATED

    for word in positive_words:
        if word in text_lower:
            return EmotionTag.POSITIVE

    return EmotionTag.NEUTRAL


def get_emotion_trajectory_summary(trajectory: List[EmotionTag]) -> str:
    """
    Summarize the emotion trajectory for context injection into LLM.

    If user moved from sad → neutral, acknowledge positively.
    If consistently anxious, note the pattern.
    """
    if not trajectory:
        return "No emotional trajectory data yet."

    if len(trajectory) == 1:
        return f"User's current emotional state: {trajectory[0].value}"

    recent = trajectory[-3:]  # Last 3 emotions
    trajectory_str = " → ".join([e.value for e in recent])

    # Detect positive shift
    if len(recent) >= 2 and recent[-1] == EmotionTag.POSITIVE:
        return f"Emotion trajectory: {trajectory_str}. User seems to be feeling better."

    if len(recent) >= 2 and recent[-1] == EmotionTag.NEUTRAL and recent[-2] in (EmotionTag.SAD, EmotionTag.ANXIOUS):
        return f"Emotion trajectory: {trajectory_str}. User appears to be stabilizing."

    # Detect persistent negative state
    if all(e in (EmotionTag.SAD, EmotionTag.ANXIOUS) for e in recent):
        return f"Emotion trajectory: {trajectory_str}. User has been consistently distressed."

    return f"Emotion trajectory: {trajectory_str}."
