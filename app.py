import os
import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path

import streamlit as st
import db

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

NEXT_LEVEL_XP = 100
STATE_FILE = Path(__file__).with_name("state_store.json")

PERSONALITIES = ["Socratic", "Socratic Gamified", "Direct", "Direct Gamified"]

def base_personality(p: str) -> str:
    return p.replace(" Gamified", "")

def is_gamified(p: str = None) -> bool:
    if p is None:
        p = st.session_state.get("personality", "Socratic")
    return "Gamified" in p

LEARNING_CONCEPTS = [
    {
        "key": "silk_road",
        "title": "Silk Road Trade Routes",
        "description": "Explore the ancient trade networks connecting East and West.",
        "starter": "Guide me through the northern and southern Silk Road routes and what choices traders faced.",
        "subtopics": [
            {
                "key": "origins_expansion",
                "title": "Origins & Expansion",
                "description": "How the Silk Road began and grew",
                "unlocked": True,
                "mastered": False,
                "learning_points": [
                    "Zhang Qian's mission to Central Asia (138-126 BCE)",
                    "Han Dynasty's role in establishing trade routes",
                    "Why it's called the 'Silk Road' (Ferdinand von Richthofen, 1877)",
                    "Initial connections between China, Persia, and Rome"
                ]
            },
            {
                "key": "northern_route",
                "title": "Northern Route",
                "description": "Through Central Asia and the steppes",
                "unlocked": False,
                "mastered": False,
                "learning_points": [
                    "Path through the Eurasian steppes",
                    "Major cities: Samarkand, Bukhara, Merv",
                    "Role of nomadic tribes (Sogdians, Turks)",
                    "Climate and terrain challenges"
                ]
            },
            {
                "key": "southern_route",
                "title": "Southern Route",
                "description": "Through the oases and deserts",
                "unlocked": False,
                "mastered": False,
                "learning_points": [
                    "Path along the Taklamakan Desert oases",
                    "Major cities: Kashgar, Khotan, Dunhuang",
                    "Desert survival and caravanserais",
                    "Connection to maritime routes"
                ]
            },
            {
                "key": "goods_trade",
                "title": "Goods & Trade",
                "description": "Silk, spices, jade, and more",
                "unlocked": False,
                "mastered": False,
                "learning_points": [
                    "Chinese exports: silk, porcelain, tea, paper",
                    "Western exports: gold, silver, glassware, wool",
                    "Central Asian goods: horses, jade, spices",
                    "How goods changed value along the route"
                ]
            },
            {
                "key": "cultural_exchange",
                "title": "Cultural Exchange",
                "description": "Ideas, religions, and technologies",
                "unlocked": False,
                "mastered": False,
                "learning_points": [
                    "Spread of Buddhism from India to China",
                    "Introduction of paper and gunpowder to the West",
                    "Exchange of artistic styles and techniques",
                    "Language and writing system influences"
                ]
            },
            {
                "key": "political_powers",
                "title": "Political Powers",
                "description": "Empires controlling the routes",
                "unlocked": False,
                "mastered": False,
                "learning_points": [
                    "Han and Tang Dynasties (China)",
                    "Persian Empires (Parthian, Sasanian)",
                    "Byzantine Empire's role",
                    "Mongol Empire's impact on trade unification"
                ]
            },
        ],
    },
]

COMMUNITY_MESSAGES = [
    "Maya shared her notes on Silk Road cultural exchanges with the study circle.",
    "Jonas hit a three-day streak by tackling Silk Road questions daily.",
    "Elena just wrapped a quiz on the Northern Route—go for the next badge!",
]

TOPIC_KEYWORDS = {
    "silk_road": [
        ("culture", "Cultural interactions on the Silk Road"),
        ("cultures", "Cultural interactions on the Silk Road"),
        ("goods", "Trade goods moving along Silk Road routes"),
        ("religion", "Religious diffusion on the Silk Road"),
        ("northern", "Northern Silk Road route"),
        ("southern", "Southern Silk Road route"),
        ("trade", "Trade networks of the Silk Road"),
        ("empire", "Empires along the Silk Road"),
    ],
}


def load_persisted_state() -> Dict:
    try:
        if STATE_FILE.exists():
            with STATE_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def save_persisted_state():
    messages_payload = []
    for msg in st.session_state.get("messages", []):
        if isinstance(msg, Message):
            messages_payload.append({
                "role": msg.role,
                "content": msg.content,
                "metadata": msg.metadata,
            })
    data = {
        "xp": st.session_state.get("xp", 0),
        "level": st.session_state.get("level", 1),
        "concept_progress": st.session_state.get("concept_progress", {}),
        "subtopic_progress": st.session_state.get("subtopic_progress", {}),
        "learning_point_progress": st.session_state.get("learning_point_progress", {}),
        "current_concept": st.session_state.get("current_concept"),
        "current_subtopic": st.session_state.get("current_subtopic"),
        "current_topic": st.session_state.get("current_topic"),
        "personality": st.session_state.get("personality"),
        "challenge_active": st.session_state.get("challenge_active", False),
        "messages": messages_payload,
        # NOTE: user_id and username are NOT saved to JSON file
        # They should only exist in session state after login
        "hint_policy": st.session_state.get("hint_policy", "LIGHT_HINTS"),
        "question_depth": st.session_state.get("question_depth", "DEEP_PROBE"),
        "quiz_difficulty": st.session_state.get("quiz_difficulty", "MEDIUM"),
        "bandit_stats": st.session_state.get("bandit_stats", {}),
        "intro_sent": st.session_state.get("intro_sent", False),
        "hint_given_this_question": st.session_state.get("hint_given_this_question", False),
        "current_hint_policy": st.session_state.get("current_hint_policy"),
        "message_feedback": st.session_state.get("message_feedback", {}),
    }
    try:
        with STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        st.warning("Unable to persist XP locally.")
    try:
        user_id = st.session_state.get("user_id")
        if user_id:
            db.save_user_state(user_id, data)
    except Exception:
        pass

@dataclass
class Message:
    role: str
    content: str
    metadata: Optional[Dict] = None

def init_state():
    # Once a user is authenticated, use the database as the source of truth.
    # Do not hydrate from the local JSON file, because it is not tied to a username
    # and can leak/overwrite state between accounts.
    persisted = {} if st.session_state.get("user_id") else load_persisted_state()
    persisted_xp = persisted.get("xp", 0)
    computed_level = 1 + persisted_xp // NEXT_LEVEL_XP
    
    default_subtopic_progress = {}
    default_learning_point_progress = {}
    
    for subtopic in LEARNING_CONCEPTS[0]["subtopics"]:
        default_subtopic_progress[subtopic["key"]] = {
            "unlocked": subtopic.get("unlocked", False),
            "mastered": subtopic.get("mastered", False),
        }
        default_learning_point_progress[subtopic["key"]] = {
            "lp_0": "locked",
            "lp_1": "locked",
            "lp_2": "locked",
            "lp_3": "locked",
        }
        if subtopic.get("unlocked"):
            default_learning_point_progress[subtopic["key"]]["lp_0"] = "active"
    
    default_concept_progress = {
        concept["key"]: {
            "unlocked": True if idx == 0 else False,
            "mastered": False,
        }
        for idx, concept in enumerate(LEARNING_CONCEPTS)
    }
    
    persisted_concepts = persisted.get("concept_progress")
    if isinstance(persisted_concepts, dict):
        for key, entry in default_concept_progress.items():
            stored = persisted_concepts.get(key)
            if isinstance(stored, dict):
                entry["unlocked"] = bool(stored.get("unlocked", entry["unlocked"]))
                entry["mastered"] = bool(stored.get("mastered", entry["mastered"]))
    
    persisted_subtopics = persisted.get("subtopic_progress")
    if isinstance(persisted_subtopics, dict):
        for key, entry in default_subtopic_progress.items():
            stored = persisted_subtopics.get(key)
            if isinstance(stored, dict):
                entry["unlocked"] = bool(stored.get("unlocked", entry["unlocked"]))
                entry["mastered"] = bool(stored.get("mastered", entry["mastered"]))
    
    persisted_lp = persisted.get("learning_point_progress")
    if isinstance(persisted_lp, dict):
        for key, entry in default_learning_point_progress.items():
            stored = persisted_lp.get(key)
            if isinstance(stored, dict):
                for lp_key in ["lp_0", "lp_1", "lp_2", "lp_3"]:
                    if lp_key in stored:
                        entry[lp_key] = stored[lp_key]
    
    # Initialize default bandit stats with user feedback tracking
    default_bandit_stats = {
        "hint_policy_rewards": {"NO_AUTOMATIC_HINTS": [], "LIGHT_HINTS": [], "FULL_HINTS": []},
        "depth_rewards": {"SHALLOW_CHECK": [], "DEEP_PROBE": []},
        "difficulty_rewards": {"EASY": [], "MEDIUM": [], "HARD": []},
        "user_feedback_rewards": {"NO_AUTOMATIC_HINTS": [], "LIGHT_HINTS": [], "FULL_HINTS": []},
        "personality_feedback": {"Socratic": [], "Socratic Gamified": [], "Direct": [], "Direct Gamified": []},
        "response_quality_scores": [],
    }
    
    defaults = {
        "page": "User Home",
        "xp": persisted_xp,
        "level": max(persisted.get("level", 1), computed_level),
        "messages": [],
        "personality": persisted.get("personality", "Socratic"),
        "awaiting_answer": False,
        "question_type": None,
        "pdf_uploaded": False,
        "pdf_file_ref": None,
        "current_topic": persisted.get("current_topic", "General Tutoring"),
        "chat_session": None,
        "chat_session_personality": None,
        "chat_session_pdf_id": None,
        "intro_sent": persisted.get("intro_sent", False),
        "current_concept": persisted.get("current_concept", LEARNING_CONCEPTS[0]["key"]),
        "current_subtopic": persisted.get("current_subtopic", "origins_expansion"),
        "concept_progress": default_concept_progress,
        "subtopic_progress": default_subtopic_progress,
        "learning_point_progress": persisted.get("learning_point_progress", {}),
        "community_pointer": 0,
        "challenge_active": persisted.get("challenge_active", False),
        "topic_refresh_counter": 0,
        "editing_message_idx": None,
        "db_state_loaded": False,
        "quiz_score": 0,
        "quiz_total": 0,
        "quiz_mode": False,
        # NOTE: user_id and username start as None and are only set by login
        # Do NOT load from JSON file to prevent auto-login bypass
        "user_id": None,
        "username": None,
        "message_count_for_lp_update": 0,
        "hint_policy": persisted.get("hint_policy", "LIGHT_HINTS"),
        "question_depth": persisted.get("question_depth", "DEEP_PROBE"),
        "quiz_difficulty": persisted.get("quiz_difficulty", "MEDIUM"),
        "last_question_time": None,
        "question_attempts": 0,
        "bandit_stats": persisted.get("bandit_stats", default_bandit_stats),
        "turns_since_lp_check": 0,
        "hint_given_this_question": persisted.get("hint_given_this_question", False),
        "current_hint_policy": persisted.get("current_hint_policy"),
        "just_awarded_xp": False,
        "pending_xp_context": None,
        # New: Track user feedback on messages (message_idx -> "up" or "down")
        "message_feedback": persisted.get("message_feedback", {}),
        # New: Track the last question asked to avoid repeats
        "last_question_asked": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Ensure bandit_stats has new keys for user feedback
    bandit_stats = st.session_state.get("bandit_stats", {})
    if "user_feedback_rewards" not in bandit_stats:
        bandit_stats["user_feedback_rewards"] = {"NO_AUTOMATIC_HINTS": [], "LIGHT_HINTS": [], "FULL_HINTS": []}
    if "personality_feedback" not in bandit_stats:
        bandit_stats["personality_feedback"] = {"Socratic": [], "Socratic Gamified": [], "Direct": [], "Direct Gamified": []}
    if "response_quality_scores" not in bandit_stats:
        bandit_stats["response_quality_scores"] = []
    st.session_state.bandit_stats = bandit_stats
    
    if st.session_state.get("user_id") and not st.session_state.get("db_state_loaded"):
        st.session_state.db_state_loaded = False
    
    active_concept = get_concept()
    topic = st.session_state.get("current_topic")
    if topic in ("General Tutoring", None, "") and active_concept:
        st.session_state.current_topic = active_concept["title"]

    persisted_messages = persisted.get("messages")
    if (not st.session_state.get("messages")) and isinstance(persisted_messages, list) and persisted_messages:
        restored = []
        for payload in persisted_messages:
            if not isinstance(payload, dict):
                continue
            role = payload.get("role")
            content = payload.get("content")
            if role and content is not None:
                restored.append(
                    Message(
                        role=role,
                        content=content,
                        metadata=payload.get("metadata"),
                    )
                )
        if restored:
            st.session_state.messages = restored
            st.session_state.awaiting_answer = False
            st.session_state.question_type = None

def level_progress(xp: int) -> float:
    return min((xp % NEXT_LEVEL_XP) / NEXT_LEVEL_XP, 1.0)

def award_xp(amount: int = 15, reason: str = "", skip_rerun: bool = False):
    """Award XP with visible notification."""
    if not is_gamified(st.session_state.get("personality")):
        return
    st.session_state.xp += amount
    new_level = 1 + st.session_state.xp // NEXT_LEVEL_XP
    leveled_up = False
    if new_level > st.session_state.level:
        st.session_state.level = new_level
        leveled_up = True
    
    # Show visible XP notification
    if reason:
        st.success(f"🌟 **+{amount} XP** earned: {reason}")
        st.toast(f"+{amount} XP: {reason}", icon="⭐")
    
    save_persisted_state()
    
    if leveled_up:
        st.balloons()
        st.success(f"🎉 **Level Up!** You're now level {new_level}!")
    
    if not skip_rerun:
        st.rerun()

_genai_import_error: Optional[str] = None
try:
    import google.generativeai as genai
except Exception as e:
    _genai_import_error = str(e)
    genai = None

_groq_import_error: Optional[str] = None
try:
    from groq import Groq
except Exception as e:
    _groq_import_error = str(e)
    Groq = None

def get_ai_model():
    """Return a configured AI model (Groq or Gemini) or None if not available.
    
    Tries Groq first (better free tier), falls back to Gemini.
    Returns dict with provider info and model/client.
    """
    # Try Groq first (14,400 requests/day vs Gemini's 1,500)
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        try:
            groq_key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            pass
    
    if groq_key and Groq is not None:
        try:
            client = Groq(api_key=groq_key)
            return {
                "provider": "groq",
                "client": client,
                "model": "llama-3.1-70b-versatile"
            }
        except Exception:
            pass
    
    # Fall back to Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        try:
            gemini_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            pass
    
    if gemini_key and genai is not None:
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            return {
                "provider": "gemini",
                "model": model
            }
        except Exception:
            pass
    
    return None

def upload_pdf_to_gemini(pdf_path: str):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return None
    try:
        genai.configure(api_key=api_key)
        uploaded_file = genai.upload_file(pdf_path)
        return uploaded_file
    except Exception as e:
        st.error(f"Error uploading PDF: {e}")
        return None

PERSONALITY_PROMPTS = {
    "Socratic": '''You are a Socratic-style history tutor who guides students through layered questioning so they uncover answers themselves.

CURRENT SUBTOPIC STRUCTURE:
You must cover specific learning points for each subtopic. The current subtopic has 4 key learning points you need to address. Stay focused on these points and avoid tangents.

ADAPTIVE TEACHING STYLE (INJECTED DYNAMICALLY):
{question_depth_instruction}
{hint_policy_instruction}
{quiz_difficulty_instruction}

YOUR TEACHING FLOW:

**FIRST TIME teaching a learning point:**
1. Provide 2-3 sentences of essential context/information about that learning point
2. Then ask ONE NEW [MINI-Q] question that helps them think deeper about what you just taught
3. This is NOT a quiz - you're helping them explore and understand the concept

**WHEN STUDENT ANSWERS your question:**
1. ALWAYS acknowledge their response first ("Good thinking about...", "I see you're considering...", "That's a thoughtful connection...")
2. Build on their answer:
   - If correct/insightful: Add 1-2 sentences that expand on their idea, then move to the next learning point
   - If partially correct: Affirm what's right, then gently add missing context
   - If incorrect: "Interesting thought, but let me add some context..." then correct gently
3. Then:
   - If they've grasped this learning point: Move to the NEXT learning point (teach new content + ask a NEW question)
   - If they need more depth: Ask ONE DIFFERENT follow-up question on the same learning point (never repeat the exact same question)
4. CRITICAL: NEVER repeat a question you just asked. Always ask a NEW question or move to a NEW learning point
5. NEVER say "I'm waiting for your answer" - always engage with what they just said

**PROGRESSION:**
- Each learning point takes 2-4 exchanges (teach → ask → respond to answer → maybe follow-up)
- After covering ALL 4 learning points, present a final synthesis [QUIZ] question
- When user gets quiz right, the subtopic is mastered

CRITICAL RULES:
- Questions should help them think about implications, connections, or reasons - NOT test memorization
- ONE question at a time, never multiple questions in one response
- NEVER ask the same question twice - if you need a follow-up, ask a DIFFERENT question about the same concept
- If a student responds, ENGAGE with that response - don't ignore it
- Stay laser-focused on the 4 learning points for the current subtopic
- Use [MINI-Q] tag before every question (10 XP per thoughtful answer)
- Use [QUIZ] tag for the final synthesis question (25 XP)
- After [QUIZ] is answered correctly, ask which subtopic to explore next

Tone: patient, encouraging, guide-like. Teach first, then help them think deeper. ALWAYS engage with student responses. NEVER repeat questions.
''',

    "Direct": '''You are a direct, structured history tutor who delivers curriculum-aligned lessons clearly and efficiently.

CURRENT SUBTOPIC STRUCTURE:
You must teach specific learning points for each subtopic. The current subtopic has 4 key learning points you need to cover.

ADAPTIVE TEACHING STYLE (INJECTED DYNAMICALLY):
{quiz_difficulty_instruction}

YOUR TEACHING FLOW:
1. Present learning points 1-2 together in a substantial paragraph (5-7 sentences)
2. End with: "Click 'Continue' when ready for the next section, or ask any questions in the chat."
3. When user says continue/next, present learning points 3-4 together in another substantial paragraph (5-7 sentences)
4. End with: "That covers the key concepts! Click 'Continue' to take the quiz, or ask questions if needed."
5. When user says continue/next/quiz, present exactly 3 [QUIZ] questions one at a time
6. Quiz difficulty should match the injected difficulty setting
7. User must get 3/3 correct to master the subtopic
8. If they miss any, re-teach that specific point briefly and quiz again
9. When user gets 3/3, congratulate and ask which subtopic to explore next

**WHEN STUDENT ASKS QUESTIONS:**
- Answer their question directly and clearly in 2-3 sentences
- Connect answer back to the learning points
- Then prompt them to continue: "Does that help? Click 'Continue' when ready."

CRITICAL RULES:
- Teach in 2 substantial chunks (points 1-2, then points 3-4)
- Each chunk should be 5-7 sentences with clear explanations and examples
- DO NOT ask yes/no questions like "Ready?" or "Any questions?"
- Instead say: "Click 'Continue' when ready" or similar
- User advances by typing "continue", "next", or clicking a button
- NO [MINI-Q] tags - only teach, then quiz at the end
- Each [QUIZ] question is worth 25 XP
- After 3/3 correct, the subtopic is mastered and sidebar updates

QUIZ FORMAT:
"Let's test your understanding with a quiz on [subtopic name]"
[QUIZ] Question 1: [question about points 1-2 at appropriate difficulty]
(wait for answer and feedback)
[QUIZ] Question 2: [question about points 3-4 at appropriate difficulty]
(wait for answer and feedback)
[QUIZ] Question 3: [synthesis question across all points at appropriate difficulty]

Tone: friendly, clear, efficient. Give substantial explanations before moving on. Engage with student questions.
'''
}

INTRO_PROMPTS = {
    "Socratic": (
        "Welcome! I'll guide you through the Silk Road using the Socratic method. "
        "I'll teach you each concept first with clear information, then ask questions to help you think deeper about what we just learned. "
        "For each subtopic, I have 4 specific learning points to cover. Let's start with Origins & Expansion. "
        "Ready to begin?"
    ),
    "Direct": (
        "Welcome! I'll teach you about the Silk Road in a clear, structured way. "
        "For each subtopic, I'll present the material in 2 sections, then give you a 3-question quiz. "
        "You'll click 'Continue' between sections and can ask questions anytime. "
        "You need 3/3 correct to master each subtopic. Let's start with Origins & Expansion. "
        "Ready to begin?"
    ),
}

def get_personality_prompt(personality: str) -> str:
    return PERSONALITY_PROMPTS.get(base_personality(personality), PERSONALITY_PROMPTS["Direct"])


def get_concept(key: Optional[str] = None):
    lookup = key or st.session_state.get("current_concept")
    for concept in LEARNING_CONCEPTS:
        if concept["key"] == lookup:
            return concept
    return LEARNING_CONCEPTS[0]


def get_current_learning_points() -> List[str]:
    """Get the learning points for the current subtopic."""
    current_subtopic_key = st.session_state.get("current_subtopic")
    if not current_subtopic_key:
        return []
    
    for concept in LEARNING_CONCEPTS:
        for subtopic in concept.get("subtopics", []):
            if subtopic["key"] == current_subtopic_key:
                return subtopic.get("learning_points", [])
    return []


def update_learning_point_progress():
    """Update learning point progress based on recent conversation."""
    current_subtopic = st.session_state.get("current_subtopic")
    if not current_subtopic:
        return
    
    learning_points = get_current_learning_points()
    if not learning_points:
        return
    
    if "learning_point_progress" not in st.session_state:
        st.session_state.learning_point_progress = {}
    if current_subtopic not in st.session_state.learning_point_progress:
        st.session_state.learning_point_progress[current_subtopic] = {}
    
    recent_messages = st.session_state.messages[-6:] if len(st.session_state.messages) >= 6 else st.session_state.messages
    conversation_text = " ".join([
        msg.content if isinstance(msg, Message) else (msg.get("content", "") if isinstance(msg, dict) else "")
        for msg in recent_messages if msg
    ]).lower()
    
    lp_progress = st.session_state.learning_point_progress[current_subtopic]
    
    for idx, point in enumerate(learning_points):
        lp_key = f"lp_{idx}"
        current_status = lp_progress.get(lp_key, "locked")
        
        point_lower = point.lower()
        key_terms = []
        
        words = point_lower.split()
        for word in words:
            clean_word = word.strip('.,()[]{}":;!?')
            if len(clean_word) > 4 and clean_word not in ['about', 'their', 'which', 'where', 'these', 'those', 'through', 'between']:
                key_terms.append(clean_word)
        
        matches = sum(1 for term in key_terms if term in conversation_text)
        
        if matches >= 2 and current_status != "completed":
            if current_status == "locked":
                lp_progress[lp_key] = "active"
            elif current_status == "active":
                recent_text = " ".join([
                    str(m.content) if isinstance(m, Message) else str(m.get("content", "")) if isinstance(m, dict) else ""
                    for m in recent_messages if m
                ])
                if matches >= 3 or "[MINI-Q]" in recent_text:
                    lp_progress[lp_key] = "completed"


def mark_episode_mastered(episode_num: int):
    """Mark a specific episode (learning point) as mastered."""
    current_subtopic = st.session_state.get("current_subtopic")
    if not current_subtopic:
        return
    
    if "learning_point_progress" not in st.session_state:
        st.session_state.learning_point_progress = {}
    if current_subtopic not in st.session_state.learning_point_progress:
        st.session_state.learning_point_progress[current_subtopic] = {
            "lp_0": "locked", "lp_1": "locked", "lp_2": "locked", "lp_3": "locked"
        }
    
    lp_key = f"lp_{episode_num - 1}"  # episode_1 = lp_0
    st.session_state.learning_point_progress[current_subtopic][lp_key] = "completed"
    
    # Activate next episode if available
    if episode_num < 4:
        next_lp_key = f"lp_{episode_num}"
        if st.session_state.learning_point_progress[current_subtopic].get(next_lp_key, "locked") == "locked":
            st.session_state.learning_point_progress[current_subtopic][next_lp_key] = "active"
    
    save_persisted_state()


def mark_subtopic_mastered(key: str):
    progress = st.session_state.subtopic_progress.get(key)
    if not progress:
        return
    if not progress["mastered"]:
        progress["mastered"] = True
        
        if key in st.session_state.learning_point_progress:
            for lp_key in st.session_state.learning_point_progress[key]:
                st.session_state.learning_point_progress[key][lp_key] = "completed"
        
        subtopics = LEARNING_CONCEPTS[0]["subtopics"]
        index = next((idx for idx, s in enumerate(subtopics) if s["key"] == key), None)
        if index is not None and index + 1 < len(subtopics):
            next_key = subtopics[index + 1]["key"]
            unlock_subtopic(next_key)
            st.session_state.current_subtopic = next_key
            st.toast("New subtopic unlocked!", icon="🚀")
        save_persisted_state()


def get_current_subtopic_status():
    """Check if current subtopic is mastered to avoid redundant teaching."""
    current_subtopic = st.session_state.get("current_subtopic")
    if not current_subtopic:
        return "not_started"
    
    progress = st.session_state.subtopic_progress.get(current_subtopic, {})
    if progress.get("mastered"):
        return "mastered"
    
    lp_progress = st.session_state.learning_point_progress.get(current_subtopic, {})
    completed_count = sum(1 for status in lp_progress.values() if status == "completed")
    
    if completed_count >= 3:
        return "nearly_complete"
    elif completed_count >= 1:
        return "in_progress"
    else:
        return "not_started"


def select_bandit_action(action_type: str, context: Dict) -> str:
    """Epsilon-greedy contextual bandit selection with user feedback integration."""
    import random
    
    epsilon = 0.15  # Reduced epsilon to favor learned preferences
    
    bandit_stats = st.session_state.get("bandit_stats", {})
    
    if action_type == "hint_policy":
        actions = ["NO_AUTOMATIC_HINTS", "LIGHT_HINTS", "FULL_HINTS"]
        rewards_key = "hint_policy_rewards"
        user_feedback_key = "user_feedback_rewards"
    elif action_type == "question_depth":
        actions = ["SHALLOW_CHECK", "DEEP_PROBE"]
        rewards_key = "depth_rewards"
        user_feedback_key = None
    elif action_type == "quiz_difficulty":
        actions = ["EASY", "MEDIUM", "HARD"]
        rewards_key = "difficulty_rewards"
        user_feedback_key = None
    else:
        return st.session_state.get(action_type, "MEDIUM")
    
    if random.random() < epsilon:
        selected = random.choice(actions)
    else:
        avg_rewards = {}
        for action in actions:
            # Combine automatic rewards with user feedback (weighted)
            auto_rewards = bandit_stats.get(rewards_key, {}).get(action, [])
            auto_avg = sum(auto_rewards) / len(auto_rewards) if auto_rewards else 0.5
            
            # User feedback is weighted more heavily (2x)
            if user_feedback_key:
                user_rewards = bandit_stats.get(user_feedback_key, {}).get(action, [])
                user_avg = sum(user_rewards) / len(user_rewards) if user_rewards else 0.5
                # Combine: 40% auto, 60% user feedback
                avg_rewards[action] = 0.4 * auto_avg + 0.6 * user_avg
            else:
                avg_rewards[action] = auto_avg
        
        selected = max(avg_rewards, key=avg_rewards.get)
    
    return selected


def record_bandit_reward(action_type: str, action: str, reward: float):
    """Record reward for a bandit action."""
    bandit_stats = st.session_state.get("bandit_stats", {
        "hint_policy_rewards": {"NO_AUTOMATIC_HINTS": [], "LIGHT_HINTS": [], "FULL_HINTS": []},
        "depth_rewards": {"SHALLOW_CHECK": [], "DEEP_PROBE": []},
        "difficulty_rewards": {"EASY": [], "MEDIUM": [], "HARD": []},
        "user_feedback_rewards": {"NO_AUTOMATIC_HINTS": [], "LIGHT_HINTS": [], "FULL_HINTS": []},
        "personality_feedback": {"Socratic": [], "Socratic Gamified": [], "Direct": [], "Direct Gamified": []},
        "response_quality_scores": [],
    })
    
    if action_type == "hint_policy":
        rewards_key = "hint_policy_rewards"
    elif action_type == "question_depth":
        rewards_key = "depth_rewards"
    elif action_type == "quiz_difficulty":
        rewards_key = "difficulty_rewards"
    elif action_type == "user_feedback":
        rewards_key = "user_feedback_rewards"
    elif action_type == "personality":
        rewards_key = "personality_feedback"
    else:
        return
    
    if rewards_key not in bandit_stats:
        bandit_stats[rewards_key] = {}
    if action not in bandit_stats[rewards_key]:
        bandit_stats[rewards_key][action] = []
    
    bandit_stats[rewards_key][action].append(reward)
    
    # Keep last 30 rewards for user feedback (more history for stability)
    max_history = 30 if action_type in ["user_feedback", "personality"] else 20
    if len(bandit_stats[rewards_key][action]) > max_history:
        bandit_stats[rewards_key][action] = bandit_stats[rewards_key][action][-max_history:]
    
    st.session_state.bandit_stats = bandit_stats
    save_persisted_state()


def record_user_feedback(message_idx: int, feedback: str):
    """
    Record user thumbs up/down feedback and update bandit rewards.
    
    Args:
        message_idx: Index of the message being rated
        feedback: "up" for thumbs up, "down" for thumbs down
    """
    # Store feedback in session state
    if "message_feedback" not in st.session_state:
        st.session_state.message_feedback = {}
    
    st.session_state.message_feedback[str(message_idx)] = feedback
    
    # Get the message metadata to understand context
    if message_idx < len(st.session_state.messages):
        msg = st.session_state.messages[message_idx]
        metadata = msg.metadata if isinstance(msg, Message) else msg.get("metadata", {})
        metadata = metadata or {}
        
        # Convert feedback to reward value
        reward = 1.0 if feedback == "up" else 0.0
        
        # Get current settings that were active for this message
        hint_policy = metadata.get("hint_policy") or st.session_state.get("current_hint_policy") or st.session_state.get("hint_policy", "LIGHT_HINTS")
        personality = st.session_state.get("personality", "Socratic")
        
        # Record rewards for the bandit system
        record_bandit_reward("user_feedback", hint_policy, reward)
        record_bandit_reward("personality", personality, reward)
        
        # Track overall response quality
        bandit_stats = st.session_state.get("bandit_stats", {})
        if "response_quality_scores" not in bandit_stats:
            bandit_stats["response_quality_scores"] = []
        bandit_stats["response_quality_scores"].append({
            "feedback": feedback,
            "personality": personality,
            "hint_policy": hint_policy,
            "timestamp": time.time(),
        })
        # Keep last 50 quality scores
        if len(bandit_stats["response_quality_scores"]) > 50:
            bandit_stats["response_quality_scores"] = bandit_stats["response_quality_scores"][-50:]
        st.session_state.bandit_stats = bandit_stats
    
    save_persisted_state()
    
    # Show subtle acknowledgment
    if feedback == "up":
        st.toast("Thanks for the feedback!", icon="👍")
    else:
        st.toast("Thanks - we'll try to improve!", icon="👎")


def get_feedback_stats() -> Dict:
    """Get aggregated feedback statistics for display."""
    bandit_stats = st.session_state.get("bandit_stats", {})
    quality_scores = bandit_stats.get("response_quality_scores", [])
    
    if not quality_scores:
        return {"total": 0, "positive": 0, "negative": 0, "rate": 0}
    
    total = len(quality_scores)
    positive = sum(1 for s in quality_scores if s.get("feedback") == "up")
    negative = total - positive
    rate = (positive / total * 100) if total > 0 else 0
    
    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "rate": round(rate, 1),
    }


def calculate_hint_effectiveness_reward(
    hint_policy: str,
    hint_was_given: bool,
    answer_correct: bool,
    response_time: float,
    attempt_count: int
) -> float:
    """
    Calculate reward for hint policy effectiveness.
    """
    base_reward = 0.0
    
    if answer_correct:
        base_reward = 0.6
        
        if response_time < 60:
            base_reward += 0.2
        elif response_time < 120:
            base_reward += 0.1
        
        if attempt_count == 1:
            base_reward += 0.2
        elif attempt_count == 2:
            base_reward += 0.1
        
        if hint_policy == "NO_AUTOMATIC_HINTS" and hint_was_given:
            base_reward -= 0.1
        
        if hint_policy == "LIGHT_HINTS" and answer_correct and not hint_was_given:
            base_reward += 0.1
            
    else:
        base_reward = 0.2
        
        if hint_was_given:
            if hint_policy == "FULL_HINTS":
                base_reward -= 0.1
            elif hint_policy == "LIGHT_HINTS":
                base_reward -= 0.05
        else:
            if hint_policy == "NO_AUTOMATIC_HINTS":
                base_reward -= 0.1
    
    return max(0.0, min(1.0, base_reward))


def check_learning_point_understanding():
    """Check if learner has understood current learning point."""
    current_subtopic = st.session_state.get("current_subtopic")
    if not current_subtopic:
        return False
    
    recent_messages = st.session_state.messages[-6:] if len(st.session_state.messages) >= 6 else st.session_state.messages
    if len(recent_messages) < 4:
        return False
    
    lp_progress = st.session_state.learning_point_progress.get(current_subtopic, {})
    current_lp_idx = None
    for idx in range(4):
        lp_key = f"lp_{idx}"
        status = lp_progress.get(lp_key, "locked")
        if status == "active":
            current_lp_idx = idx
            break
    
    if current_lp_idx is None:
        return False
    
    substantive_answers = 0
    for msg in recent_messages[-4:]:
        if isinstance(msg, Message) and msg.role == "user":
            if len(msg.content.split()) >= 6:
                substantive_answers += 1
    
    if substantive_answers >= 2:
        lp_key = f"lp_{current_lp_idx}"
        lp_progress[lp_key] = "completed"
        
        if current_lp_idx + 1 < 4:
            next_lp_key = f"lp_{current_lp_idx + 1}"
            if lp_progress.get(next_lp_key, "locked") == "locked":
                lp_progress[next_lp_key] = "active"
        
        st.session_state.learning_point_progress[current_subtopic] = lp_progress
        save_persisted_state()
        return True
    
    return False


def unlock_subtopic(key: str):
    progress = st.session_state.subtopic_progress.setdefault(key, {"unlocked": False, "mastered": False})
    if not progress["unlocked"]:
        progress["unlocked"] = True
        save_persisted_state()


def rotate_community_message() -> str:
    pointer = st.session_state.get("community_pointer", 0) % len(COMMUNITY_MESSAGES)
    message = COMMUNITY_MESSAGES[pointer]
    st.session_state.community_pointer = (pointer + 1) % len(COMMUNITY_MESSAGES)
    return message


def derive_topic_label(raw_text: str, concept_key: str) -> str:
    if not raw_text:
        return get_concept(concept_key)["title"]
    lowered = raw_text.lower().strip()
    for keyword, label in TOPIC_KEYWORDS.get(concept_key, []):
        if keyword in lowered:
            return label
    return get_concept(concept_key)["title"]


def refresh_topic_periodically():
    st.session_state.topic_refresh_counter += 1
    if st.session_state.topic_refresh_counter >= 6:
        recent_user = next(
            (m.content for m in reversed(st.session_state.messages) if m.role == "user"),
            "",
        )
        st.session_state.current_topic = derive_topic_label(recent_user, st.session_state.current_concept)
        st.session_state.topic_refresh_counter = 0


def build_tutor_context(personality: str, pdf_ref=None, continuation_context: str = None) -> str:
    """Build context for tutor, with optional continuation context after XP award."""
    base_prompt = get_personality_prompt(personality)
    
    quiz_difficulty = st.session_state.get("quiz_difficulty", "MEDIUM")
    
    if quiz_difficulty == "EASY":
        quiz_diff_instruction = "QUIZ DIFFICULTY: EASY - Ask straightforward recall questions with obvious answers."
    elif quiz_difficulty == "HARD":
        quiz_diff_instruction = "QUIZ DIFFICULTY: HARD - Ask synthesis questions requiring deep analysis and connections."
    else:
        quiz_diff_instruction = "QUIZ DIFFICULTY: MEDIUM - Ask questions requiring understanding and application."
    
    bp = base_personality(personality)
    gamified = is_gamified(personality)

    if bp == "Socratic":
        question_depth = st.session_state.get("question_depth", "DEEP_PROBE")
        hint_policy = st.session_state.get("hint_policy", "LIGHT_HINTS")

        if question_depth == "DEEP_PROBE":
            depth_instruction = "QUESTION DEPTH: DEEP - Ask at least 2 follow-up why/how questions about the same concept before moving to the next learning point."
        else:
            depth_instruction = "QUESTION DEPTH: SHALLOW - Ask one quick understanding check per learning point, then advance if correct."

        if hint_policy == "NO_AUTOMATIC_HINTS":
            hint_instruction = "HINT POLICY: Only provide hints if student explicitly asks 'can I get a hint?' or similar."
        elif hint_policy == "FULL_HINTS":
            hint_instruction = "HINT POLICY: After one wrong or weak answer, provide a detailed scaffolded hint pointing toward the answer."
        else:
            hint_instruction = "HINT POLICY: After one wrong answer, give a small nudge ('Think about...') without giving away the answer."

        context = base_prompt.format(
            question_depth_instruction=depth_instruction,
            hint_policy_instruction=hint_instruction,
            quiz_difficulty_instruction=quiz_diff_instruction
        )
    else:
        context = base_prompt.format(
            quiz_difficulty_instruction=quiz_diff_instruction
        )

    if bp == "Direct":
        context += "\n\nIMPORTANT: Only use [QUIZ] tags for the 3-question quiz at the end. Do not use [MINI-Q] tags."
    else:
        context += "\n\nIMPORTANT: Use [MINI-Q] and [QUIZ] tags. Keep responses concise. NEVER repeat the exact same question twice."

    if gamified:
        if bp == "Socratic":
            context += "\n- Award +10 XP when the student shows reasoning or cites evidence."
        else:
            context += "\n- Award 25 XP for each correct [QUIZ] answer. Students must get 3/3 to master the subtopic."

    current_subtopic_key = st.session_state.get("current_subtopic")
    if current_subtopic_key:
        for concept in LEARNING_CONCEPTS:
            for subtopic in concept.get("subtopics", []):
                if subtopic["key"] == current_subtopic_key:
                    learning_points = subtopic.get("learning_points", [])
                    if learning_points:
                        context += f"\n\nCURRENT SUBTOPIC: {subtopic['title']}"
                        context += f"\n\nYou must cover these 4 learning points in order:"
                        for i, point in enumerate(learning_points, 1):
                            context += f"\n{i}. {point}"
                        context += "\n\nStay focused on these points. Do not add extra details or explore tangents."
    
    if pdf_ref:
        context += (
            "\n\nCURRICULUM INTEGRATION: Use the uploaded PDF only as background knowledge. "
            "Summarise or paraphrase ideas in fresh language. Never quote the PDF verbatim."
        )
    
    active_concept = get_concept()
    if active_concept:
        context += (
            f"\n\nACTIVE CONCEPT: Focus on '{active_concept['title']}'. "
            f"Starter idea: {active_concept['description']}"
        )
    
    # Add last question tracking to prevent repeats
    last_question = st.session_state.get("last_question_asked")
    if last_question and bp == "Socratic":
        context += f"\n\nLAST QUESTION ASKED: \"{last_question}\"\nIMPORTANT: Do NOT ask this exact question again. If you need a follow-up, ask a DIFFERENT question about the same concept."
    
    if continuation_context:
        context += f"\n\n{continuation_context}"
    
    return context


def chat_with_tutor(model_info, personality: str, user_message: str, pdf_ref=None, continuation_prompt: str = None) -> str:
    """Chat with the tutor model with defensive error handling.
    
    Supports both Groq and Gemini providers.
    """
    if model_info is None:
        return "(Error: AI model not initialized. Please check your GROQ_API_KEY or GEMINI_API_KEY configuration and try again.)"
    
    provider = model_info["provider"]
    
    try:
        # Build system context
        system_context = build_tutor_context(personality, pdf_ref, continuation_prompt)
        
        if provider == "groq":
            # Groq uses OpenAI-style chat completions
            client = model_info["client"]
            model_name = model_info["model"]
            
            # Build message history
            messages = [{"role": "system", "content": system_context}]
            
            # Add conversation history
            for msg in st.session_state.get("messages", []):
                role = msg.role if isinstance(msg, Message) else msg.get("role")
                content = msg.content if isinstance(msg, Message) else msg.get("content")
                if role in ["user", "assistant"]:
                    messages.append({"role": role, "content": content})
            
            # Add current message
            if continuation_prompt:
                user_message_with_context = f"{user_message}\n\n[SYSTEM NOTE: {continuation_prompt}]"
                messages.append({"role": "user", "content": user_message_with_context})
            else:
                messages.append({"role": "user", "content": user_message})
            
            # Call Groq API
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )
            
            reply_text = response.choices[0].message.content
            
            if not reply_text or reply_text.strip() == "":
                st.error("Tutor generated an empty response. Please try again.")
                return "I'm having trouble generating a response right now. Could you please rephrase your question or try again?"
            
            return reply_text
        
        elif provider == "gemini":
            # Gemini uses its own session-based approach
            model = model_info["model"]
            pdf_id = getattr(pdf_ref, "name", None) or getattr(pdf_ref, "uri", None)
            chat = st.session_state.get("chat_session")
            needs_reset = (
                chat is None
                or st.session_state.get("chat_session_personality") != personality
                or st.session_state.get("chat_session_pdf_id") != pdf_id
            )

            if needs_reset:
                chat_history = [{"role": "user", "parts": [system_context]}]
                chat = model.start_chat(history=chat_history)
                st.session_state.chat_session = chat
                st.session_state.chat_session_personality = personality
                st.session_state.chat_session_pdf_id = pdf_id

            message_to_send = user_message
            if continuation_prompt:
                message_to_send = f"{user_message}\n\n[SYSTEM NOTE: {continuation_prompt}]"

            if pdf_ref:
                response = chat.send_message([message_to_send, pdf_ref])
            else:
                response = chat.send_message(message_to_send)

            reply_text = getattr(response, "text", "") or ""
            
            if not reply_text or reply_text.strip() == "":
                st.error("Tutor generated an empty response. Please try again.")
                return "I'm having trouble generating a response right now. Could you please rephrase your question or try again?"
            
            return reply_text
        
        else:
            return f"Unknown provider: {provider}"
    
    except Exception as e:
        st.session_state.chat_session = None
        st.error(f"Chat error: {e}")
        return f"I encountered an error while processing your request: {e}. Please try again."


def parse_tutor_response(response: str):
    """Parse tutor response for tags and signals."""
    question_type = None
    mastered_episode = None
    subtopic_complete = False
    
    if "[MASTERED episode_" in response:
        import re
        match = re.search(r'\[MASTERED episode_(\d+)\]', response)
        if match:
            mastered_episode = int(match.group(1))
            response = re.sub(r'\[MASTERED episode_\d+\]', '', response).strip()
    
    if "[SUBTOPIC_COMPLETE]" in response:
        subtopic_complete = True
        response = response.replace("[SUBTOPIC_COMPLETE]", "").strip()
    
    if "[MINI-Q]" in response:
        question_type = "mini"
        response = response.replace("[MINI-Q]", "**Mini-Question:**")
        
        # Track the question to avoid repeats
        question_match = response.split("**Mini-Question:**")[-1].strip()
        if "?" in question_match:
            question_text = question_match.split("?")[0] + "?"
            st.session_state.last_question_asked = question_text.strip()
    elif "[QUIZ]" in response:
        question_type = "quiz"
        response = response.replace("[QUIZ]", "**Quiz:**")
    elif ("+10 XP" in response or "+10XP" in response or "+ 10 XP" in response):
        question_type = "mini"
        if "?" in response:
            response = "**Mini-Question:** " + response
    elif ("+5 XP" in response or "+5XP" in response):
        question_type = "mini"
        if "?" in response:
            response = "**Mini-Question:** " + response
    
    return response, question_type, mastered_episode, subtopic_complete


def ensure_initial_tutor_message(model_info):
    """Ensure intro message is sent only once, with defensive checks."""
    if st.session_state.intro_sent:
        return
    if st.session_state.messages:
        st.session_state.intro_sent = True
        save_persisted_state()
        return
    if model_info is None:
        return

    personality = st.session_state.personality
    prompt = INTRO_PROMPTS.get(base_personality(personality), INTRO_PROMPTS["Direct"])

    try:
        with st.spinner("Tutor is getting ready..."):
            reply = chat_with_tutor(
                model_info,
                personality,
                prompt,
                st.session_state.pdf_file_ref,
            )
        
        if not reply or reply.strip() == "":
            st.error("Tutor generated an empty intro response.")
            reply = f"Welcome! I'm your {personality} tutor. Let's begin exploring the Silk Road together. What would you like to learn about first?"
    except Exception as e:
        st.error(f"Error initializing tutor: {e}")
        reply = f"Welcome! I'm your {personality} tutor. Let's begin exploring the Silk Road together. What would you like to learn about first?"

    clean_reply, question_type, mastered_episode, subtopic_complete = parse_tutor_response(reply)

    # Store current hint policy in message metadata for feedback tracking
    msg_metadata = {
        "question_type": question_type,
        "hint_policy": st.session_state.get("hint_policy", "LIGHT_HINTS"),
        "personality": personality,
    }
    
    st.session_state.messages.append(
        Message(role="assistant", content=clean_reply, metadata=msg_metadata)
    )

    if question_type:
        st.session_state.awaiting_answer = True
        st.session_state.question_type = question_type
        st.session_state.current_hint_policy = st.session_state.get("hint_policy", "LIGHT_HINTS")
        st.session_state.hint_given_this_question = False

    st.session_state.intro_sent = True
    save_persisted_state()


def check_answer_quality(user_answer: str, question_type: str, personality: str):
    words = user_answer.strip().split()
    bp = base_personality(personality)
    if len(words) < 2:
        return False, 0, ""

    if bp == "Direct" and question_type == "quiz":
        if not st.session_state.get("quiz_mode"):
            st.session_state.quiz_mode = True
            st.session_state.quiz_score = 0
            st.session_state.quiz_total = 0

        if len(words) >= 3:
            return True, 25, "Quiz question"
        return False, 0, ""

    if question_type == "quiz":
        return True, 25, "Quiz mastery"

    lower_answer = user_answer.lower()
    word_count = len(words)
    cleaned = " ".join(lower_answer.split()).strip()
    exact_invalid = {
        "idk", "i don't know", "i dont know", "no idea",
        "not sure", "no clue", "?", "??", "???",
    }
    substring_invalid = {
        "i don't know", "i dont know", "dont know", "don't know",
    }
    if cleaned in exact_invalid or any(sub in cleaned for sub in substring_invalid):
        return False, 0, ""

    if bp == "Socratic":
        if word_count >= 6:
            return True, 10, "Thoughtful response"
        return False, 0, ""

    return False, 0, ""


def render_feedback_buttons(message_idx: int):
    """Render subtle thumbs up/down buttons for a message."""
    feedback_key = str(message_idx)
    current_feedback = st.session_state.get("message_feedback", {}).get(feedback_key)
    
    # Create a container for the feedback buttons
    col1, col2, col3 = st.columns([1, 1, 10])
    
    with col1:
        # Thumbs up button
        up_style = "primary" if current_feedback == "up" else "secondary"
        up_disabled = current_feedback is not None
        if st.button(
            "👍",
            key=f"thumbs_up_{message_idx}",
            type=up_style,
            disabled=up_disabled,
            help="This response was helpful"
        ):
            record_user_feedback(message_idx, "up")
            st.rerun()
    
    with col2:
        # Thumbs down button
        down_style = "primary" if current_feedback == "down" else "secondary"
        down_disabled = current_feedback is not None
        if st.button(
            "👎",
            key=f"thumbs_down_{message_idx}",
            type=down_style,
            disabled=down_disabled,
            help="This response could be better"
        ):
            record_user_feedback(message_idx, "down")
            st.rerun()


def render_concept_tracker():
    concept = LEARNING_CONCEPTS[0]

    rows = []
    for subtopic in concept["subtopics"]:
        key = subtopic["key"]
        progress = st.session_state.get("subtopic_progress", {}).get(key, {
            "unlocked": subtopic.get("unlocked", False),
            "mastered": subtopic.get("mastered", False)
        })
        is_current = key == st.session_state.get("current_subtopic")
        learning_points = subtopic.get("learning_points", [])
        lp_progress = st.session_state.get("learning_point_progress", {}).get(key, {})
        total = len(learning_points)
        completed = sum(1 for i in range(total) if lp_progress.get(f"lp_{i}") == "completed")
        active_idx = next((i for i in range(total) if lp_progress.get(f"lp_{i}") == "active"), None)
        rows.append((subtopic, key, progress, is_current, learning_points, total, completed, active_idx))

    html_parts = ["<div style='font-size:0.82em;line-height:1.6;'>"]
    for subtopic, key, progress, is_current, learning_points, total, completed, active_idx in rows:
        if progress.get("mastered"):
            icon = "✅"
            title_color = "#2e7d32"
            bg = "#f1f8f1"
            border = "#a5d6a7"
        elif is_current:
            icon = "▶"
            title_color = "#1565c0"
            bg = "#e8f0fe"
            border = "#90caf9"
        elif progress.get("unlocked"):
            icon = "○"
            title_color = "#555"
            bg = "#fafafa"
            border = "#ddd"
        else:
            icon = "🔒"
            title_color = "#aaa"
            bg = "#f5f5f5"
            border = "#eee"

        html_parts.append(
            f"<div style='border:1px solid {border};border-radius:6px;padding:6px 8px;margin-bottom:6px;background:{bg};'>"
            f"<div style='color:{title_color};font-weight:600;'>{icon} {subtopic['title']}</div>"
        )

        if (progress.get("unlocked") or is_current) and total > 0:
            pct = int(completed / total * 100)
            bar_filled = "#4caf50" if progress.get("mastered") else "#5dade2"
            html_parts.append(
                f"<div style='margin-top:4px;display:flex;align-items:center;gap:6px;'>"
                f"<div style='flex:1;background:#e0e0e0;border-radius:4px;height:5px;'>"
                f"<div style='width:{pct}%;background:{bar_filled};height:5px;border-radius:4px;'></div></div>"
                f"<span style='color:#777;font-size:0.9em;white-space:nowrap;'>{completed}/{total}</span>"
                f"</div>"
            )
            for idx, point in enumerate(learning_points):
                lp_key = f"lp_{idx}"
                status = lp_progress.get(lp_key, "locked")
                if status == "completed":
                    dot = "✓"; dot_color = "#4caf50"
                elif status == "active":
                    dot = "→"; dot_color = "#1565c0"
                else:
                    dot = "·"; dot_color = "#bbb"
                short = point if len(point) <= 42 else point[:39] + "…"
                html_parts.append(
                    f"<div style='margin-left:1em;margin-top:2px;color:#666;'>"
                    f"<span style='color:{dot_color};font-weight:bold;'>{dot}</span> {short}</div>"
                )

        html_parts.append("</div>")

    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def sidebar_nav():
    with st.sidebar:
        st.markdown("## TutorQuest")
        username = st.session_state.get("username", "Guest")
        st.caption(f"Welcome, **{username}**!")
        
        st.markdown("### Navigate")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Home", use_container_width=True, type="primary" if st.session_state.page == "User Home" else "secondary"):
                st.session_state.page = "User Home"
                st.rerun()
        with col2:
            if st.button("Chat", use_container_width=True, type="primary" if st.session_state.page == "Tutoring Chat" else "secondary"):
                st.session_state.page = "Tutoring Chat"
                st.rerun()
        
        st.divider()
        
        if st.session_state.page == "Tutoring Chat":
            st.markdown("### Tutor Mode")
            if st.session_state.personality not in PERSONALITIES:
                st.session_state.personality = "Socratic"

            descriptions = {
                "Socratic": "Guided questioning, no XP",
                "Socratic Gamified": "Guided questioning + XP & levels",
                "Direct": "Structured lessons, no XP",
                "Direct Gamified": "Structured lessons + XP & levels",
            }

            for p in PERSONALITIES:
                is_active = st.session_state.personality == p
                button_type = "primary" if is_active else "secondary"
                ind_col, btn_col = st.columns([0.06, 0.94])
                with ind_col:
                    if is_active:
                        st.markdown(
                            "<div style='background:#1565c0;width:3px;height:34px;"
                            "border-radius:2px;margin-top:3px;'></div>",
                            unsafe_allow_html=True
                        )
                with btn_col:
                    _clicked = st.button(f"{p}", use_container_width=True, type=button_type, key=f"personality_{p}")
                if _clicked and p != st.session_state.personality:
                    st.session_state.personality = p
                    st.session_state.chat_session = None
                    st.session_state.chat_session_personality = None
                    st.session_state.chat_session_pdf_id = None
                    st.session_state.messages = []
                    st.session_state.awaiting_answer = False
                    st.session_state.question_type = None
                    st.session_state.current_topic = "General Tutoring"
                    st.session_state.intro_sent = False
                    st.session_state.message_feedback = {}
                    st.session_state.last_question_asked = None
                    save_persisted_state()
                    st.rerun()

            st.caption(descriptions[st.session_state.personality])
            st.divider()
        
        if is_gamified():
            st.metric("Level", st.session_state.level)
            st.metric("XP", st.session_state.xp)
            st.progress(level_progress(st.session_state.xp))
        st.markdown("### Silk Road Progress")
        render_concept_tracker()
        
        st.divider()
        
        # Show feedback stats
        feedback_stats = get_feedback_stats()
        if feedback_stats["total"] > 0:
            st.markdown("### Your Feedback")
            st.caption(f"👍 {feedback_stats['positive']} • 👎 {feedback_stats['negative']}")
            st.caption(f"Satisfaction: {feedback_stats['rate']}%")
            st.divider()
        
        if len(st.session_state.messages) > 0:
            chat_export = []
            for msg in st.session_state.messages:
                if isinstance(msg, Message):
                    chat_export.append({"role": msg.role, "content": msg.content})
                elif isinstance(msg, dict):
                    chat_export.append({"role": msg.get("role", "unknown"), "content": msg.get("content", "")})
            
            chat_json = json.dumps(chat_export, indent=2)
            
            st.download_button(
                label="Download Chat History",
                data=chat_json,
                file_name=f"silk_road_chat_{st.session_state.current_subtopic}.json",
                mime="application/json",
                use_container_width=True
            )
        
        st.divider()
        
        with st.container(border=True):
            st.markdown("#### Profile")
            username = st.session_state.get("username", "Guest")
            st.markdown(f"**{username}**")
            if is_gamified():
                st.caption(f"Level {st.session_state.level} • {st.session_state.xp} XP")
            if st.button("Sign Out", use_container_width=True, type="secondary"):
                # Clear the JSON file to prevent auto-login
                try:
                    if STATE_FILE.exists():
                        STATE_FILE.unlink()
                except Exception:
                    pass
                # Clear all session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()


def page_home():
    st.title("Welcome back")
    st.caption("Track your learning streaks, XP, and level progress.")

    col_main, col_side = st.columns([2.6, 1.4])

    with col_main:
        with st.container(border=True):
            st.subheader("Current progress")
            st.metric("Level", st.session_state.level)
            st.metric("XP", st.session_state.xp)
            current = st.session_state.xp % NEXT_LEVEL_XP
            remaining = NEXT_LEVEL_XP - current
            st.progress(
                level_progress(st.session_state.xp),
                text=f"{current}/{NEXT_LEVEL_XP} • {remaining} XP to next level",
            )
            
            # Real stats from actual activity
            questions_answered = len([m for m in st.session_state.messages if m.role == "user"])
            mini_qs_completed = sum(1 for m in st.session_state.messages 
                                   if hasattr(m, "metadata") and m.metadata 
                                   and m.metadata.get("type") == "mini" 
                                   and m.metadata.get("xp_awarded", 0) > 0)
            quizzes_completed = sum(1 for m in st.session_state.messages 
                                   if hasattr(m, "metadata") and m.metadata 
                                   and m.metadata.get("type") == "quiz" 
                                   and m.metadata.get("xp_awarded", 0) > 0)
            
            s1, s2, s3 = st.columns(3)
            s1.metric("Questions Answered", questions_answered, help="Total questions you've answered")
            s2.metric("Mini-Qs Earned", mini_qs_completed, help="Mini-questions where you earned XP")
            s3.metric("Quizzes Passed", quizzes_completed, help="Quiz questions answered correctly")

    with col_side:
        with st.container(border=True):
            st.subheader("Badges Earned")
            badges = []
            
            # Badges based on actual achievements
            if st.session_state.level >= 2:
                badges.append("🎯 Focused Learner")
            if st.session_state.level >= 5:
                badges.append("📚 Knowledge Seeker")
            if st.session_state.xp >= 100:
                badges.append("💯 Century Club")
            
            # Check if user has completed any subtopics
            mastered_count = sum(1 for progress in st.session_state.subtopic_progress.values() 
                               if progress.get("mastered", False))
            if mastered_count >= 1:
                badges.append("✅ First Mastery")
            if mastered_count >= 3:
                badges.append("🌟 Master Scholar")
            
            # Check for engagement badges
            questions_answered = len([m for m in st.session_state.messages if m.role == "user"])
            if questions_answered >= 10:
                badges.append("💬 Engaged Learner")
            if questions_answered >= 50:
                badges.append("🚀 Learning Champion")
            
            if badges:
                for badge in badges:
                    st.write(badge)
            else:
                st.caption("🏆 Earn badges by learning with your tutor!")
                st.caption("• Reach level 2 for your first badge")
                st.caption("• Complete subtopics to unlock more")
        st.markdown("\n")
        with st.container(border=True):
            st.subheader("Next goals")
            st.markdown("- Complete a tutor chat\n- Answer a Mini-Q\n- Finish a quiz round")
        
        # Show feedback summary on home page
        feedback_stats = get_feedback_stats()
        if feedback_stats["total"] > 0:
            st.markdown("\n")
            with st.container(border=True):
                st.subheader("Tutor Feedback")
                st.markdown(f"**{feedback_stats['rate']}%** satisfaction")
                st.caption(f"Based on {feedback_stats['total']} ratings")

    st.markdown("---")
    st.subheader("Daily Learning")
    st.caption("Start your learning journey and build your daily streak!")
    
    # Daily streak tracker (automatic, not clickable)
    st.markdown("### 🔥 Daily Streak")
    col_streak1, col_streak2 = st.columns([1, 3])
    with col_streak1:
        st.metric("Current Streak", "0 days", help="Complete at least one learning session daily to build your streak")
    with col_streak2:
        st.caption("💡 **Tip:** Answer questions with your tutor to maintain your streak and earn XP!")
    
    st.markdown("\n")
    st.markdown("### Quick Start Learning")
    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("🧠 Start Practice Session", use_container_width=True, type="primary"):
            st.session_state.page = "Tutoring Chat"
            st.session_state.challenge_active = False
            st.toast("Let's practice! Answer questions to earn XP.", icon="🎓")
            st.rerun()
    with a2:
        if st.button("📚 Begin New Lesson", use_container_width=True):
            st.session_state.page = "Tutoring Chat"
            st.session_state.challenge_active = False
            # Reset to start fresh lesson
            st.session_state.messages = []
            st.session_state.intro_sent = False
            st.session_state.chat_session = None
            st.toast("Starting new lesson! Engage with the tutor to earn XP.", icon="📖")
            st.rerun()
    with a3:
        if st.button("⚡ Challenge Question", use_container_width=True):
            st.session_state.page = "Tutoring Chat"
            st.session_state.challenge_active = True
            st.toast("Challenge armed! Answer correctly for bonus XP.", icon="⚡")
            save_persisted_state()
            st.rerun()

    st.info(
        "💎 **Earn XP by learning!** Use a Gamified tutor mode and answer questions:\n"
        "- Socratic Gamified: 10 XP per thoughtful answer\n"
        "- Direct Gamified: 25 XP per quiz question\n"
        "- Challenge bonus: +10 XP extra"
    )


def page_chat():
    st.title("Tutoring Chat")
    personality = st.session_state.personality
    
    if is_gamified(personality):
        st.caption(f"Learning with **{personality}** tutor • Answer questions to earn XP")
    else:
        st.caption(f"Learning with **{personality}** tutor")
    
    st.markdown(f"**Current Topic:** {st.session_state.current_topic}")

    model_info = get_ai_model()
    if model_info is None:
        st.error("AI API key not configured. Please set GROQ_API_KEY or GEMINI_API_KEY in your environment or Streamlit secrets.")
        return
    
    # Show which provider is being used
    provider = model_info.get("provider", "unknown")
    if provider == "groq":
        st.caption("🚀 Using Groq (Llama 3.1 70B)")
    elif provider == "gemini":
        st.caption("✨ Using Google Gemini")

    with st.expander("Upload Curriculum (PDF)", expanded=not st.session_state.pdf_uploaded):
        uploaded_file = st.file_uploader(
            "Upload a PDF for the tutor to reference",
            type=["pdf"],
            help="The tutor will use this document"
        )
        
        if uploaded_file and not st.session_state.pdf_uploaded:
            pdf_path = f"/tmp/{uploaded_file.name}"
            with open(pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            with st.spinner("Uploading PDF..."):
                pdf_ref = upload_pdf_to_gemini(pdf_path)
                if pdf_ref:
                    st.session_state.pdf_file_ref = pdf_ref
                    st.session_state.pdf_uploaded = True
                    st.session_state.chat_session = None
                    st.session_state.chat_session_personality = None
                    st.session_state.chat_session_pdf_id = None
                    st.session_state.messages = []
                    st.session_state.awaiting_answer = False
                    st.session_state.question_type = None
                    st.session_state.current_topic = "General Tutoring"
                    st.session_state.intro_sent = False
                    st.session_state.topic_refresh_counter = 0
                    st.session_state.message_feedback = {}
                    st.session_state.last_question_asked = None
                    save_persisted_state()
                    st.success(f"PDF uploaded: {uploaded_file.name}")
                    st.rerun()
    
    local_pdf = Path("/Users/alishajain/Gamified_app/silk_roads.pdf")
    if local_pdf.exists() and not st.session_state.pdf_uploaded:
        if st.button("Load Silk Roads Curriculum"):
            with st.spinner("Loading curriculum..."):
                pdf_ref = upload_pdf_to_gemini(str(local_pdf))
                if pdf_ref:
                    st.session_state.pdf_file_ref = pdf_ref
                    st.session_state.pdf_uploaded = True
                    st.session_state.chat_session = None
                    st.session_state.chat_session_personality = None
                    st.session_state.chat_session_pdf_id = None
                    st.session_state.messages = []
                    st.session_state.awaiting_answer = False
                    st.session_state.question_type = None
                    st.session_state.current_topic = "General Tutoring"
                    st.session_state.intro_sent = False
                    st.session_state.topic_refresh_counter = 0
                    st.session_state.message_feedback = {}
                    st.session_state.last_question_asked = None
                    save_persisted_state()
                    st.success("Curriculum loaded!")
                    st.rerun()

    chip_query = None
    chip_topic = None

    st.markdown("#### Silk Road Learning Routes")
    
    active_concept = get_concept()
    if st.session_state.current_topic in ("General Tutoring", "", None):
        st.session_state.current_topic = active_concept["title"]
    st.caption(f"{active_concept['description']}")

    primer_col, challenge_col = st.columns([1, 1])
    with primer_col:
        if st.button("Route primer", use_container_width=True, help="Get an overview and learning roadmap for the Silk Road topic"):
            chip_query = active_concept["starter"]
            chip_topic = active_concept["title"]
    with challenge_col:
        if st.button("Challenge Question", use_container_width=True, help="Get a tough synthesis question on everything discussed"):
            challenge_prompt = "Give me a challenge question on everything we've discussed in this chat so far. This should test deep synthesis and understanding across multiple concepts."
            
            st.session_state.messages.append(Message(role="user", content=challenge_prompt, metadata=None))
            save_persisted_state()
            
            try:
                with st.spinner("Preparing challenge question..."):
                    reply = chat_with_tutor(model_info, personality, challenge_prompt, st.session_state.pdf_file_ref)
                
                if not reply or reply.strip() == "":
                    reply = "Here's a challenge question: How did the geographic, political, and cultural factors of the Silk Road interact to shape the flow of trade and ideas between East and West?"
            except Exception as e:
                st.error(f"Chat error: {e}")
                reply = f"I encountered an error: {e}. Here's a backup challenge: How did the Silk Road transform both Eastern and Western civilizations?"
            
            clean_reply, question_type, mastered_episode, subtopic_complete = parse_tutor_response(reply)
            
            msg_metadata = {
                "question_type": question_type,
                "hint_policy": st.session_state.get("hint_policy", "LIGHT_HINTS"),
                "personality": personality,
            }
            st.session_state.messages.append(Message(role="assistant", content=clean_reply, metadata=msg_metadata))
            
            st.session_state.awaiting_answer = True
            st.session_state.question_type = question_type or "quiz"
            st.session_state.challenge_active = True
            st.session_state.current_hint_policy = st.session_state.get("hint_policy", "LIGHT_HINTS")
            st.session_state.hint_given_this_question = False
            save_persisted_state()
            st.rerun()

    st.markdown("##### Quick starts:")
    pp1, pp2, pp3, pp4 = st.columns([1.4, 1.6, 1.8, 2])
    
    _socratic_starts = [
        ("Northern Route", "Guide me through the northern Silk Road route with questions."),
        ("Trade Goods", "Help me reason through what goods were traded on the Silk Road."),
        ("Cultural Exchange", "Ask me guiding questions about cultural exchange on the Silk Road.")
    ]
    _direct_starts = [
        ("Silk Road Origins", "Teach me about the origins and expansion of the Silk Road."),
        ("Route Comparison", "Walk me through the northern vs. southern Silk Road routes."),
        ("Political Powers", "Give me a clear outline of empires controlling the Silk Road.")
    ]
    quick_starts = {
        "Socratic": _socratic_starts,
        "Socratic Gamified": _socratic_starts,
        "Direct": _direct_starts,
        "Direct Gamified": _direct_starts,
    }

    starts = quick_starts.get(personality, _direct_starts)
    with pp1:
        if st.button(starts[0][0], use_container_width=True):
            chip_query = starts[0][1]
            chip_topic = starts[0][0]
    with pp2:
        if st.button(starts[1][0], use_container_width=True):
            chip_query = starts[1][1]
            chip_topic = starts[1][0]
    with pp3:
        if st.button(starts[2][0], use_container_width=True):
            chip_query = starts[2][1]
            chip_topic = starts[2][0]
    with pp4:
        if st.button("Surprise me", use_container_width=True):
            chip_query = f"Give me a fresh angle on {active_concept['title']} with a question to get started."
            chip_topic = active_concept["title"]
    
    ensure_initial_tutor_message(model_info)

    # Render chat messages with feedback buttons
    with st.container(border=True):
        for idx, m in enumerate(st.session_state.messages):
            if isinstance(m, dict):
                role = m.get("role")
                content = m.get("content")
                metadata = m.get("metadata")
            else:
                role = m.role
                content = m.content
                metadata = m.metadata if hasattr(m, "metadata") else None
            
            with st.chat_message(role):
                if role == "user":
                    col1, col2 = st.columns([6, 1])
                    with col1:
                        if st.session_state.get("editing_message_idx") == idx:
                            edited_text = st.text_area(
                                "Edit message", value=content, key=f"edit_{idx}", label_visibility="collapsed"
                            )
                            if st.button("Save", key=f"save_{idx}"):
                                if isinstance(st.session_state.messages[idx], dict):
                                    st.session_state.messages[idx]["content"] = edited_text
                                else:
                                    st.session_state.messages[idx].content = edited_text
                                st.session_state.editing_message_idx = None
                                st.session_state.messages = st.session_state.messages[:idx+1]
                                
                                # Clear feedback for removed messages
                                keys_to_remove = [k for k in st.session_state.message_feedback.keys() if int(k) > idx]
                                for k in keys_to_remove:
                                    del st.session_state.message_feedback[k]
                                
                                # Reset question tracking
                                st.session_state.last_question_asked = None
                                
                                try:
                                    with st.spinner("Tutor is thinking..."):
                                        reply = chat_with_tutor(model_info, personality, edited_text, st.session_state.pdf_file_ref)
                                    
                                    if not reply or reply.strip() == "":
                                        reply = "I'm having trouble generating a response. Could you please try rephrasing your question?"
                                except Exception as e:
                                    st.error(f"Chat error: {e}")
                                    reply = f"I encountered an error: {e}. Please try again."
                                
                                clean_reply, question_type, mastered_episode, subtopic_complete = parse_tutor_response(reply)
                                
                                if subtopic_complete:
                                    mark_subtopic_mastered(st.session_state.current_subtopic)
                                    st.toast("Chapter complete! Subtopic mastered!", icon="🎉")
                                
                                msg_metadata = {
                                    "question_type": question_type,
                                    "hint_policy": st.session_state.get("hint_policy", "LIGHT_HINTS"),
                                    "personality": personality,
                                }
                                st.session_state.messages.append(
                                    Message(role="assistant", content=clean_reply, metadata=msg_metadata)
                                )
                                
                                if question_type:
                                    st.session_state.awaiting_answer = True
                                    st.session_state.question_type = question_type
                                    st.session_state.current_hint_policy = st.session_state.get("hint_policy", "LIGHT_HINTS")
                                    st.session_state.hint_given_this_question = False
                                
                                save_persisted_state()
                                st.rerun()
                        else:
                            st.markdown(content)
                    with col2:
                        if st.session_state.get("editing_message_idx") != idx:
                            if st.button("Edit", key=f"edit_btn_{idx}"):
                                st.session_state.editing_message_idx = idx
                                st.rerun()
                else:
                    # Assistant message - show content and feedback buttons
                    st.markdown(content)
                    
                    # Render subtle feedback buttons beneath assistant messages
                    render_feedback_buttons(idx)

    user_input = st.chat_input("Ask a question or answer the tutor...")
    query = chip_query or user_input
    
    if query:
        topic_update = None
        if chip_topic:
            topic_update = chip_topic
        elif user_input and not st.session_state.awaiting_answer:
            topic_update = user_input.strip()

        st.session_state.messages.append(Message(role="user", content=query, metadata=None))
        save_persisted_state()

        pending_type = st.session_state.question_type
        continuation_prompt = None
        xp_awarded = 0
        xp_reason = ""
        
        if st.session_state.awaiting_answer and pending_type:
            current_time = time.time()
            last_time = st.session_state.get("last_question_time")
            response_time = current_time - last_time if last_time is not None else 0
            
            is_valid, xp, reason = check_answer_quality(query, pending_type, personality)
            
            hint_policy = st.session_state.get("current_hint_policy", "LIGHT_HINTS")
            hint_given = st.session_state.get("hint_given_this_question", False)
            attempt_count = st.session_state.get("question_attempts", 1)
            
            hint_reward = calculate_hint_effectiveness_reward(
                hint_policy=hint_policy,
                hint_was_given=hint_given,
                answer_correct=(is_valid and xp > 0),
                response_time=response_time,
                attempt_count=attempt_count
            )
            record_bandit_reward("hint_policy", hint_policy, hint_reward)
            
            if pending_type == "quiz":
                if response_time < 120 and is_valid and xp > 0:
                    difficulty_reward = 1.0
                elif response_time < 120 and not is_valid:
                    difficulty_reward = 0.3
                else:
                    difficulty_reward = 0.0 if response_time > 180 else 0.5
                
                record_bandit_reward("quiz_difficulty", st.session_state.get("quiz_difficulty", "MEDIUM"), difficulty_reward)
                
                context = {"level": st.session_state.level, "xp": st.session_state.xp}
                st.session_state.quiz_difficulty = select_bandit_action("quiz_difficulty", context)
            
            if base_personality(personality) == "Socratic":
                if is_valid and xp > 0:
                    if response_time < 90:
                        depth_reward = 1.0
                    elif response_time < 180:
                        depth_reward = 0.7
                    else:
                        depth_reward = 0.4
                elif "idk" not in query.lower() and "don't know" not in query.lower():
                    depth_reward = 0.4
                else:
                    depth_reward = 0.1
                
                record_bandit_reward("question_depth", st.session_state.get("question_depth", "DEEP_PROBE"), depth_reward)
                
                context = {"engagement": depth_reward, "level": st.session_state.level}
                st.session_state.question_depth = select_bandit_action("question_depth", context)
            
            context = {"level": st.session_state.level, "personality": personality}
            st.session_state.hint_policy = select_bandit_action("hint_policy", context)
            
            if is_valid and xp > 0:
                xp_awarded = xp
                xp_reason = reason or f"{pending_type.title()} response"
                
                metadata = {
                    "type": pending_type,
                    "xp_awarded": xp,
                    "reason": reason,
                    "personality": personality,
                    "response_time": response_time,
                }
                
                if st.session_state.challenge_active:
                    xp_awarded += 10
                    xp_reason += " + Challenge bonus"
                    metadata["challenge_bonus"] = 10
                    st.session_state.challenge_active = False
                
                if pending_type == "quiz":
                    mark_subtopic_mastered(st.session_state.current_subtopic)
                
                st.session_state.messages[-1].metadata = metadata
                
                if base_personality(personality) == "Socratic":
                    continuation_prompt = f"The learner gave a thoughtful response and earned {xp_awarded} XP. Acknowledge their thinking and continue to the next question or learning point naturally. IMPORTANT: Move forward - do not ask the exact same question again. If they've grasped this concept, move to the NEXT learning point. If they need more depth, ask a DIFFERENT follow-up question."
                else:
                    continuation_prompt = f"The learner answered correctly and earned {xp_awarded} XP. Provide brief positive feedback and continue with the next quiz question or learning section."
                
                save_persisted_state()
            else:
                if st.session_state.challenge_active:
                    st.toast("Challenge bonus still waiting for a strong answer.", icon="⌛")
                st.session_state.question_attempts = st.session_state.get("question_attempts", 0) + 1
            
            st.session_state.awaiting_answer = False
            st.session_state.question_type = None
        elif topic_update:
            concept_key = st.session_state.current_concept
            st.session_state.current_topic = derive_topic_label(topic_update, concept_key)
            st.session_state.topic_refresh_counter = 0
            save_persisted_state()

        try:
            with st.spinner("Tutor is thinking..."):
                reply = chat_with_tutor(model_info, personality, query, st.session_state.pdf_file_ref, continuation_prompt)
            
            if not reply or reply.strip() == "":
                st.error("Tutor generated an empty response")
                reply = "I'm having trouble generating a response right now. Could you please rephrase your question or try again?"
        except Exception as e:
            st.error(f"Chat error: {e}")
            reply = f"I encountered an error while processing your request: {e}. Please try again."

        clean_reply, question_type, mastered_episode, subtopic_complete = parse_tutor_response(reply)
        
        if subtopic_complete:
            mark_subtopic_mastered(st.session_state.current_subtopic)
            st.toast("Chapter complete! Subtopic mastered!", icon="🎉")
        
        # Store metadata including current bandit settings for feedback tracking
        msg_metadata = {
            "question_type": question_type,
            "hint_policy": st.session_state.get("hint_policy", "LIGHT_HINTS"),
            "personality": personality,
        }
        st.session_state.messages.append(
            Message(role="assistant", content=clean_reply, metadata=msg_metadata)
        )
        
        # Show XP notification AFTER adding the message but BEFORE rerun
        if xp_awarded > 0:
            award_xp(xp_awarded, xp_reason, skip_rerun=True)
        
        refresh_topic_periodically()
        
        st.session_state.message_count_for_lp_update += 1
        
        update_learning_point_progress()
        if base_personality(personality) == "Socratic" and st.session_state.message_count_for_lp_update >= 3:
            st.session_state.message_count_for_lp_update = 0
            if check_learning_point_understanding():
                st.toast("Learning point mastered!", icon="✓")
        
        save_persisted_state()
        
        if question_type:
            st.session_state.awaiting_answer = True
            st.session_state.question_type = question_type
            st.session_state.last_question_time = time.time()
            st.session_state.question_attempts = 1
            st.session_state.current_hint_policy = st.session_state.get("hint_policy", "LIGHT_HINTS")
            st.session_state.hint_given_this_question = False
            
            if question_type == "quiz":
                context = {"level": st.session_state.level, "xp": st.session_state.xp}
                st.session_state.quiz_difficulty = select_bandit_action("quiz_difficulty", context)
        
        st.rerun()

    # Bottom section with Continue buttons for Direct, Reset, and status
    if base_personality(personality) == "Direct" and len(st.session_state.messages) > 1:
        col_cont1, col_cont2, col_cont3 = st.columns([1, 1, 1])
        with col_cont1:
            if st.button("Continue", use_container_width=True, type="primary", key="continue_btn_bottom"):
                query = "continue"
                st.session_state.messages.append(Message(role="user", content=query, metadata=None))
                save_persisted_state()
                
                try:
                    with st.spinner("Tutor is thinking..."):
                        reply = chat_with_tutor(model_info, personality, query, st.session_state.pdf_file_ref)
                    
                    if not reply or reply.strip() == "":
                        reply = "Let me continue with the next section of our lesson..."
                except Exception as e:
                    st.error(f"Chat error: {e}")
                    reply = f"I encountered an error: {e}. Please try again."
                
                clean_reply, question_type, mastered_episode, subtopic_complete = parse_tutor_response(reply)
                msg_metadata = {
                    "question_type": question_type,
                    "hint_policy": st.session_state.get("hint_policy", "LIGHT_HINTS"),
                    "personality": personality,
                }
                st.session_state.messages.append(Message(role="assistant", content=clean_reply, metadata=msg_metadata))
                if question_type:
                    st.session_state.awaiting_answer = True
                    st.session_state.question_type = question_type
                    st.session_state.current_hint_policy = st.session_state.get("hint_policy", "LIGHT_HINTS")
                    st.session_state.hint_given_this_question = False
                save_persisted_state()
                st.rerun()
        with col_cont2:
            if st.button("Ready for Quiz", use_container_width=True, key="quiz_btn_bottom"):
                query = "I'm ready for the quiz"
                st.session_state.messages.append(Message(role="user", content=query, metadata=None))
                save_persisted_state()
                
                try:
                    with st.spinner("Preparing quiz..."):
                        reply = chat_with_tutor(model_info, personality, query, st.session_state.pdf_file_ref)
                    
                    if not reply or reply.strip() == "":
                        reply = "[QUIZ] Question 1: What was the primary purpose of Zhang Qian's mission to the West?"
                except Exception as e:
                    st.error(f"Chat error: {e}")
                    reply = f"I encountered an error: {e}. Please try again."
                
                clean_reply, question_type, mastered_episode, subtopic_complete = parse_tutor_response(reply)
                msg_metadata = {
                    "question_type": question_type,
                    "hint_policy": st.session_state.get("hint_policy", "LIGHT_HINTS"),
                    "personality": personality,
                }
                st.session_state.messages.append(Message(role="assistant", content=clean_reply, metadata=msg_metadata))
                if question_type:
                    st.session_state.awaiting_answer = True
                    st.session_state.question_type = question_type
                    st.session_state.current_hint_policy = st.session_state.get("hint_policy", "LIGHT_HINTS")
                    st.session_state.hint_given_this_question = False
                save_persisted_state()
                st.rerun()
        with col_cont3:
            if st.button("Reset chat", use_container_width=True, type="secondary"):
                st.session_state.messages = []
                st.session_state.awaiting_answer = False
                st.session_state.question_type = None
                st.session_state.current_topic = get_concept()["title"]
                st.session_state.chat_session = None
                st.session_state.chat_session_personality = None
                st.session_state.chat_session_pdf_id = None
                st.session_state.intro_sent = False
                st.session_state.challenge_active = False
                st.session_state.topic_refresh_counter = 0
                st.session_state.message_feedback = {}
                st.session_state.last_question_asked = None
                save_persisted_state()
                st.rerun()
    else:
        col_a, col_b = st.columns([1, 2])
        with col_a:
            if st.button("Reset chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.awaiting_answer = False
                st.session_state.question_type = None
                st.session_state.current_topic = get_concept()["title"]
                st.session_state.chat_session = None
                st.session_state.chat_session_personality = None
                st.session_state.chat_session_pdf_id = None
                st.session_state.intro_sent = False
                st.session_state.challenge_active = False
                st.session_state.topic_refresh_counter = 0
                st.session_state.message_feedback = {}
                st.session_state.last_question_asked = None
                save_persisted_state()
                st.rerun()
        with col_b:
            if st.session_state.awaiting_answer:
                q_type = st.session_state.question_type
                if is_gamified(personality):
                    if q_type == "mini":
                        xp_label = "10 XP for strong reasoning"
                    else:
                        xp_label = "25 XP for quiz question"
                    st.info(f"Awaiting answer • {xp_label}")
                else:
                    st.info("Awaiting answer")
            else:
                if st.session_state.challenge_active and is_gamified(personality):
                    st.caption("Challenge armed: next correct answer earns +10 bonus XP on top of regular rewards.")
                elif is_gamified(personality):
                    bp = base_personality(personality)
                    if bp == "Socratic":
                        st.caption("Mini-Q: 10 XP per thoughtful answer • Quiz: 25 XP")
                    else:
                        st.caption("Quiz: 25 XP per correct answer")

    if base_personality(personality) == "Direct":
        if st.session_state.awaiting_answer:
            if is_gamified(personality):
                st.info("Awaiting quiz answer • 25 XP per correct answer")
            else:
                st.info("Awaiting quiz answer")
        else:
            st.caption("Use 'Continue' to advance through the lesson, or type questions anytime")


def apply_styles():
    st.markdown("""
        <style>
        :root {
            --primary-500: #5dade2;
            --primary-100: #e3f2fd;
            --surface-100: #ffffff;
            --surface-200: #f4f8fc;
            --accent-100: #d6eaf8;
            --shadow-soft: 0 14px 36px rgba(45, 96, 150, 0.12);
        }

        .stApp {
            background: radial-gradient(circle at top, #f8fbff 0%, #eef4fb 60%, #ffffff 100%);
        }

        .stApp header {
            backdrop-filter: blur(12px);
            background: rgba(255, 255, 255, 0.72);
            border-bottom: 1px solid rgba(93, 173, 226, 0.18);
        }

        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 3rem;
            max-width: 1100px;
        }

        [data-testid="stSidebar"] {
            box-shadow: inset -1px 0 0 rgba(93, 173, 226, 0.15);
        }

        .stButton>button {
            border-radius: 999px;
            padding: 0.55rem 1.4rem;
            font-weight: 600;
            border: 1px solid rgba(93, 173, 226, 0.28);
            background: rgba(93, 173, 226, 0.12);
            color: #154360;
            transition: all 0.18s ease;
            box-shadow: 0 4px 12px rgba(93, 173, 226, 0.14);
        }

        .stButton>button:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 18px rgba(93, 173, 226, 0.2);
            border-color: rgba(93, 173, 226, 0.45);
            background: rgba(93, 173, 226, 0.18);
        }

        /* Subtle feedback buttons styling */
        div[data-testid="stHorizontalBlock"] .stButton>button[kind="secondary"] {
            padding: 0.25rem 0.5rem;
            font-size: 0.9rem;
            min-height: 0;
            border-radius: 8px;
            background: rgba(200, 200, 200, 0.15);
            border: 1px solid rgba(150, 150, 150, 0.2);
            box-shadow: none;
        }
        
        div[data-testid="stHorizontalBlock"] .stButton>button[kind="secondary"]:hover {
            background: rgba(93, 173, 226, 0.2);
            transform: none;
            box-shadow: none;
        }

        div[data-testid="metric-container"] {
            background: var(--surface-200);
            border-radius: 16px;
            padding: 0.75rem 1rem;
            border: 1px solid rgba(93, 173, 226, 0.25);
            box-shadow: var(--shadow-soft);
        }

        .stProgress > div > div {
            border-radius: 999px;
        }

        .concept-tracker {
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
            margin-bottom: 0.75rem;
        }

        .concept-chip {
            border-radius: 12px;
            padding: 0.5rem 0.7rem;
            font-weight: 600;
            border: 1px solid rgba(27, 38, 49, 0.08);
            background: rgba(255, 255, 255, 0.86);
            color: #1b2631;
        }

        .concept-chip.active {
            background: rgba(255, 215, 64, 0.35);
            border-color: rgba(255, 182, 0, 0.4);
        }

        .concept-chip.mastered {
            background: rgba(46, 204, 113, 0.2);
            border-color: rgba(46, 204, 113, 0.45);
        }

        .concept-chip.locked {
            background: rgba(189, 195, 199, 0.25);
            color: rgba(27, 38, 49, 0.5);
        }

        div[data-testid="stChatMessage"] {
            border-radius: 18px;
            padding: 0.4rem 0.6rem;
            margin-bottom: 0.65rem;
            background: var(--surface-100);
            box-shadow: 0 8px 24px rgba(93, 173, 226, 0.16);
        }

        div[data-testid="stChatMessageUser"] {
            background: linear-gradient(135deg, var(--primary-100) 0%, #ffffff 100%);
            border: 1px solid rgba(93, 173, 226, 0.4);
        }

        div[data-testid="stChatMessageAssistant"] {
            background: linear-gradient(135deg, #ffffff 0%, #f4f8fc 100%);
            border: 1px solid rgba(27, 38, 49, 0.08);
        }

        .stMarkdown h4, .stMarkdown h5 {
            color: #154360;
            letter-spacing: 0.01em;
        }

        .stMarkdown code, .stCodeBlock {
            border-radius: 10px !important;
            background: rgba(21, 67, 96, 0.08) !important;
        }

        [data-testid="stExpander"] {
            border-radius: 18px;
            border: 1px solid rgba(93, 173, 226, 0.35);
            background: rgba(255, 255, 255, 0.9);
            box-shadow: var(--shadow-soft);
        }

        .stCaption, .stMarkdown p {
            font-size: 0.95rem;
            line-height: 1.55;
        }

        .stChatInput>div>div {
            border-radius: 14px;
            border: 1px solid rgba(93, 173, 226, 0.4);
            box-shadow: 0 10px 22px rgba(93, 173, 226, 0.18);
            background: #ffffff;
        }
        </style>
        """, unsafe_allow_html=True)


def reset_state_for_auth(user_id, username):
    """Keep only auth identity so the next rerun starts clean and loads DB state."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.user_id = user_id
    st.session_state.username = username
    st.session_state.db_state_loaded = False


def show_login_page():
    st.title("Sign in to TutorQuest")
    st.write("Create an account or sign in to persist your progress across devices.")
    with st.form("auth_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns(2)
        with col1:
            login = st.form_submit_button("Sign in")
        with col2:
            register = st.form_submit_button("Register")
    
    if login and username and password:
        user_id = db.authenticate_user(username.strip(), password)
        if user_id:
            # Do NOT save here. Saving before loading from DB can overwrite
            # the user's saved state with defaults/local JSON state.
            reset_state_for_auth(user_id, username.strip())
            st.success(f"✅ Signed in successfully as {username.strip()}!")
            st.rerun()
        else:
            st.error(f"❌ Invalid username or password. Please check your credentials and try again.")
    
    if register and username and password:
        if len(username.strip()) < 3:
            st.error("Username must be at least 3 characters long.")
        elif len(password) < 6:
            st.error("Password must be at least 6 characters long.")
        else:
            created = db.create_user(username.strip(), password)
            if created:
                # Start a brand-new account from clean defaults instead of
                # copying whatever local JSON/session state happened to exist.
                reset_state_for_auth(created, username.strip())
                st.success(f"🎉 Account created and signed in as {username.strip()}!")
                st.rerun()
            else:
                st.error(f"❌ Could not create account. Username '{username.strip()}' may already exist.")


def main():
    st.set_page_config(
        page_title="TutorQuest",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    try:
        db.init_db()
    except Exception as e:
        st.error(f"Database initialization failed: {e}")
    
    init_state()
    apply_styles()

    if not st.session_state.get("user_id"):
        show_login_page()
        return

    if st.session_state.get("user_id") and not st.session_state.get("db_state_loaded"):
        try:
            state = db.get_user_state(st.session_state["user_id"])
            if isinstance(state, dict):
                persisted_messages = state.get("messages")
                if isinstance(persisted_messages, list) and persisted_messages:
                    restored = []
                    for payload in persisted_messages:
                        if not isinstance(payload, dict):
                            continue
                        role = payload.get("role")
                        content = payload.get("content")
                        if role and content is not None:
                            restored.append(
                                Message(
                                    role=role,
                                    content=content,
                                    metadata=payload.get("metadata"),
                                )
                            )
                    if restored:
                        st.session_state.messages = restored
                
                for k, v in state.items():
                    if k == "messages":
                        continue
                    if k in ("xp", "level", "concept_progress", "subtopic_progress", "learning_point_progress", 
                             "current_concept", "current_subtopic", "current_topic", "personality", 
                             "challenge_active", "intro_sent",
                             "hint_policy", "question_depth", "quiz_difficulty", "bandit_stats", "message_feedback"):
                        st.session_state[k] = v
                
            # Mark as loaded even when there is no saved state yet, otherwise
            # new users keep re-checking the DB on every rerun.
            st.session_state.db_state_loaded = True
        except Exception as e:
            st.error(f"Error loading saved state: {e}")

    sidebar_nav()

    if st.session_state.page == "User Home":
        page_home()
    else:
        page_chat()


if __name__ == "__main__":
    main()