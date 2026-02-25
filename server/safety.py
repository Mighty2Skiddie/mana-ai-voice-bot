"""
Safety Layer — Crisis Keyword Detection (English + Hindi)

This module implements the hardcoded, non-overridable safety layer that scans
every user transcript for crisis indicators before any LLM processing.

SAFETY PROTOCOL:
1. Detect crisis keywords in both English and Hindi
2. Never diagnose, prescribe, or ask clinical questions
3. Provide helpline resources immediately
4. Stay calm and present — never panic the user
"""

import re
from typing import List, Tuple
from server.models import SafetyResult, SafetyLevel
from server.config import HELPLINES


# ═══════════════════════════════════════════════════════════
# Crisis Keyword Database — HARDCODED, NON-OVERRIDABLE
# ═══════════════════════════════════════════════════════════

# English crisis keywords and phrases
CRISIS_KEYWORDS_EN = [
    # Direct self-harm
    "kill myself", "want to die", "end my life", "end it all",
    "suicide", "suicidal", "self harm", "self-harm", "hurt myself",
    "hurting myself", "cut myself", "cutting myself",
    # Hopelessness indicators
    "no reason to live", "better off dead", "don't want to be alive",
    "can't go on", "nothing left to live for", "wish i was dead",
    "wish i were dead", "want to disappear", "not worth living",
    # Planning indicators
    "wrote a note", "written a note", "saying goodbye", "giving away my things",
    "have a plan", "know how to end it",
    # Passive death wish
    "wouldn't mind dying", "hope i don't wake up",
    "if i didn't exist", "world without me",
]

# Hindi crisis keywords and phrases
CRISIS_KEYWORDS_HI = [
    # Direct self-harm
    "khud ko hurt karna", "khud ko maarna", "khudkushi",
    "aatmhatya", "suicide karna", "mar jaana chahta",
    "mar jaana chahti", "mar jana chahta", "mar jana chahti",
    "jeena nahi chahta", "jeena nahi chahti",
    "jina nahi chahta", "jina nahi chahti",
    # Hopelessness
    "sab khatam karna hai", "sab khatam kar dena",
    "koi faayda nahi", "koi fayda nahi",
    "jeene ka mann nahi", "jine ka mann nahi",
    "zindagi se tang", "zindagi se thak gaya",
    "zindagi se thak gayi",
    # Planning
    "plan banaya hai", "soch liya hai", "faisla kar liya",
    # Mixed / Hinglish
    "life end karna", "khud ko khatam", "apne aap ko hurt",
    "apni life khatam", "mujhe nahi jeena",
    "main nahi reh sakta", "main nahi reh sakti",
]

# Warning-level keywords (ambiguous but worth flagging)
WARNING_KEYWORDS_EN = [
    "don't want to be here", "can't take it anymore", "so done with everything",
    "tired of living", "nothing matters", "what's the point",
    "nobody cares", "no one would miss me", "burden to everyone",
    "done with life", "give up on everything",
]

WARNING_KEYWORDS_HI = [
    "thak gaya hoon sab se", "thak gayi hoon sab se",
    "kuch nahi hoga", "kisi ko fark nahi padta",
    "sab bekar hai", "main bojh hoon",
    "haar maan li", "haar man li",
    "koi matlab nahi", "khatam ho gaya sab",
]


# ═══════════════════════════════════════════════════════════
# Crisis Response Scripts — Pre-approved, bilingual
# ═══════════════════════════════════════════════════════════

CRISIS_RESPONSE_EN = (
    "What you're feeling matters, and I'm really glad you shared that with me. "
    "You don't have to go through this alone. I want to make sure you get the right support. "
    "Please reach out to one of these helplines — they're available to talk right now:\n\n"
    f"• iCall: {HELPLINES['iCall']}\n"
    f"• Vandrevala Foundation: {HELPLINES['Vandrevala Foundation']}\n"
    f"• iMind: {HELPLINES['iMind']}\n\n"
    "I'll stay here with you. Will you reach out to one of those numbers?"
)

CRISIS_RESPONSE_HI = (
    "Jo aap feel kar rahe hain woh mayne rakhta hai. Aapne bataya, yeh bahut zaroori tha. "
    "Aapko akele se nahi guzarna hai. Main chahta hoon ki aapko sahi madad mile. "
    "Please in helplines pe call karein — yeh abhi available hain:\n\n"
    f"• iCall: {HELPLINES['iCall']}\n"
    f"• Vandrevala Foundation: {HELPLINES['Vandrevala Foundation']}\n"
    f"• iMind: {HELPLINES['iMind']}\n\n"
    "Main aapke saath hoon. Kya aap in mein se kisi number pe call karenge?"
)

WARNING_RESPONSE_EN = (
    "I hear you, and what you're going through sounds really hard. "
    "I want you to know — if things ever feel too heavy, there are people who can help. "
    f"You can reach iCall at {HELPLINES['iCall']} or "
    f"Vandrevala Foundation at {HELPLINES['Vandrevala Foundation']} anytime. "
    "I'm here too. Would you like to keep talking?"
)

WARNING_RESPONSE_HI = (
    "Main sun raha hoon, aur yeh sach mein bahut mushkil lagta hai. "
    "Agar kabhi cheezein bahut bhaari lagein, toh madad ke liye log hain. "
    f"iCall pe call kar sakte hain: {HELPLINES['iCall']} ya "
    f"Vandrevala Foundation: {HELPLINES['Vandrevala Foundation']}. "
    "Main bhi yahan hoon. Kya baat karna chahenge?"
)


# ═══════════════════════════════════════════════════════════
# Safety Check Function
# ═══════════════════════════════════════════════════════════

def _normalize_text(text: str) -> str:
    """Normalize text for keyword matching — lowercase, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def _check_keywords(text: str, keywords: List[str]) -> List[str]:
    """Check text against a list of keywords, return matched ones."""
    normalized = _normalize_text(text)
    matched = []
    for keyword in keywords:
        if keyword.lower() in normalized:
            matched.append(keyword)
    return matched


def check_safety(text: str, language: str = "en") -> SafetyResult:
    """
    Scan user transcript for crisis indicators.

    This is the FIRST check run on every user message, BEFORE any LLM processing.
    It is hardcoded and cannot be overridden by system prompts or user input.

    Args:
        text: The user's transcribed message
        language: Detected language code ("en", "hi", "hi-en")

    Returns:
        SafetyResult with crisis level, matched keywords, and response script
    """
    if not text or not text.strip():
        return SafetyResult(level=SafetyLevel.SAFE)

    # Check BOTH language keyword sets regardless of detected language
    # (user might switch languages mid-crisis)
    crisis_matches_en = _check_keywords(text, CRISIS_KEYWORDS_EN)
    crisis_matches_hi = _check_keywords(text, CRISIS_KEYWORDS_HI)
    all_crisis = crisis_matches_en + crisis_matches_hi

    if all_crisis:
        # Determine response language
        if language in ("hi", "hi-en") or crisis_matches_hi:
            crisis_response = CRISIS_RESPONSE_HI
        else:
            crisis_response = CRISIS_RESPONSE_EN

        return SafetyResult(
            level=SafetyLevel.CRISIS,
            matched_keywords=all_crisis,
            crisis_response=crisis_response,
            helplines=HELPLINES,
        )

    # Check warning-level keywords
    warning_matches_en = _check_keywords(text, WARNING_KEYWORDS_EN)
    warning_matches_hi = _check_keywords(text, WARNING_KEYWORDS_HI)
    all_warnings = warning_matches_en + warning_matches_hi

    if all_warnings:
        if language in ("hi", "hi-en") or warning_matches_hi:
            warning_response = WARNING_RESPONSE_HI
        else:
            warning_response = WARNING_RESPONSE_EN

        return SafetyResult(
            level=SafetyLevel.WARNING,
            matched_keywords=all_warnings,
            crisis_response=warning_response,
            helplines=HELPLINES,
        )

    return SafetyResult(level=SafetyLevel.SAFE)


def get_crisis_response(language: str = "en") -> str:
    """Get the pre-built crisis response in the given language."""
    if language in ("hi", "hi-en"):
        return CRISIS_RESPONSE_HI
    return CRISIS_RESPONSE_EN


def get_helplines_text(language: str = "en") -> str:
    """Get formatted helpline numbers text."""
    lines = []
    for name, number in HELPLINES.items():
        lines.append(f"• {name}: {number}")
    return "\n".join(lines)
