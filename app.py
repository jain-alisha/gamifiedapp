import os
import json
from dataclasses import dataclass
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
        "user_id": st.session_state.get("user_id"),
        "username": st.session_state.get("username"),
        "hint_policy": st.session_state.get("hint_policy", "LIGHT_HINTS"),
        "question_depth": st.session_state.get("question_depth", "DEEP_PROBE"),
        "quiz_difficulty": st.session_state.get("quiz_difficulty", "MEDIUM"),
        "bandit_stats": st.session_state.get("bandit_stats", {}),
    }
    try:
        with STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        st.warning("Unable to persist XP locally.")
    # Also persist to SQLite for logged-in users
    try:
        user_id = st.session_state.get("user_id")
        if user_id:
            # store same payload to DB
            db.save_user_state(user_id, data)
    except Exception:
        # non-fatal: DB persistence shouldn't break UI
        pass

@dataclass
class Message:
    role: str
    content: str
    metadata: Optional[Dict] = None

def init_state():
    persisted = load_persisted_state()
    persisted_xp = persisted.get("xp", 0)
    computed_level = 1 + persisted_xp // NEXT_LEVEL_XP
    
    # Initialize subtopic progress for Silk Road
    default_subtopic_progress = {}
    default_learning_point_progress = {}
    
    for subtopic in LEARNING_CONCEPTS[0]["subtopics"]:
        default_subtopic_progress[subtopic["key"]] = {
            "unlocked": subtopic.get("unlocked", False),
            "mastered": subtopic.get("mastered", False),
        }
        # Initialize learning point tracking (4 points per subtopic)
        default_learning_point_progress[subtopic["key"]] = {
            "lp_0": "locked",
            "lp_1": "locked",
            "lp_2": "locked",
            "lp_3": "locked",
        }
        # If it's the first subtopic (origins_expansion), unlock first learning point
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
    
    # Load learning point progress
    persisted_lp = persisted.get("learning_point_progress")
    if isinstance(persisted_lp, dict):
        for key, entry in default_learning_point_progress.items():
            stored = persisted_lp.get(key)
            if isinstance(stored, dict):
                for lp_key in ["lp_0", "lp_1", "lp_2", "lp_3"]:
                    if lp_key in stored:
                        entry[lp_key] = stored[lp_key]
    
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
        "intro_sent": False,
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
        "user_id": persisted.get("user_id"),
        "username": persisted.get("username"),
        "message_count_for_lp_update": 0,
        # Contextual bandit state
        "hint_policy": persisted.get("hint_policy", "LIGHT_HINTS"),  # NO_AUTOMATIC_HINTS, LIGHT_HINTS, FULL_HINTS
        "question_depth": persisted.get("question_depth", "DEEP_PROBE"),  # SHALLOW_CHECK, DEEP_PROBE
        "quiz_difficulty": persisted.get("quiz_difficulty", "MEDIUM"),  # EASY, MEDIUM, HARD
        "last_question_time": None,
        "question_attempts": 0,
        "bandit_stats": persisted.get("bandit_stats", {
            "hint_policy_rewards": {"NO_AUTOMATIC_HINTS": [], "LIGHT_HINTS": [], "FULL_HINTS": []},
            "depth_rewards": {"SHALLOW_CHECK": [], "DEEP_PROBE": []},
            "difficulty_rewards": {"EASY": [], "MEDIUM": [], "HARD": []},
        }),
        "turns_since_lp_check": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # If user_id was restored but db_state_loaded is False, trigger DB load
    if st.session_state.get("user_id") and not st.session_state.get("db_state_loaded"):
        st.session_state.db_state_loaded = False  # Ensure it loads on next render
    
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
            st.session_state.intro_sent = True
            st.session_state.awaiting_answer = False
            st.session_state.question_type = None

def level_progress(xp: int) -> float:
    return min((xp % NEXT_LEVEL_XP) / NEXT_LEVEL_XP, 1.0)

def award_xp(amount: int = 15, reason: str = ""):
    st.session_state.xp += amount
    new_level = 1 + st.session_state.xp // NEXT_LEVEL_XP
    if new_level > st.session_state.level:
        st.session_state.level = new_level
        st.balloons()
        st.success(f"🎉 Level up! You're now level {new_level}!")
    if reason:
        st.toast(f"+{amount} XP: {reason}", icon="⭐")
    save_persisted_state()
    st.rerun()  # Force immediate UI update

_genai_import_error: Optional[str] = None
try:
    import google.generativeai as genai
except Exception as e:
    _genai_import_error = str(e)
    genai = None

def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            api_key = None
    if not api_key or genai is None:
        return None
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-2.5-flash")
    except Exception:
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
1. For each learning point:
   - First, provide 2-3 sentences of essential context/information about that learning point
   - Then ask ONE [MINI-Q] question that helps them think deeper about what you just taught
   - This is NOT a quiz - you're helping them explore and understand the concept
   
2. Build on their answers with follow-up context or gentle corrections
3. After covering ALL 4 learning points this way, present a final synthesis [QUIZ] question
4. When user gets quiz right, the subtopic is mastered

CRITICAL RULES:
- ALWAYS teach the core information first (2-3 sentences) before asking
- Questions should help them think about implications, connections, or reasons - NOT test if they memorized
- Example: "The Han Dynasty extended trade routes west. Why might controlling these routes have been strategically important for them?"
- ONE question at a time, never multiple questions in one response
- Stay laser-focused on the 4 learning points for the current subtopic
- Each learning point should take 2-3 exchanges: teach → ask → respond to answer
- Use [MINI-Q] tag before every question (10 XP per thoughtful answer)
- Use [QUIZ] tag for the final synthesis question (25 XP)
- After [QUIZ] is answered correctly, ask which subtopic to explore next

RESPONSE FORMAT:
[2-3 sentences teaching the learning point]

[MINI-Q] One thoughtful question about what you just taught

Tone: patient, encouraging, guide-like. Teach first, then help them think deeper.
''',

    "Narrative": '''You are a narrative-style history tutor who teaches through immersive storytelling and historical role-play.

CURRENT SUBTOPIC STRUCTURE:
You must cover specific learning points for each subtopic. The current subtopic has 4 key learning points you need to address through storytelling.

ADAPTIVE TEACHING STYLE (INJECTED DYNAMICALLY):
{quiz_difficulty_instruction}

YOUR TEACHING FLOW:
1. Frame each learning point as a short immersive scene (3-4 sentences)
2. Ask ONE [MINI-Q] question that connects the scene to the learning point
3. After student responds, reveal what happened and explain significance
4. Move to next learning point with a new scene
5. After covering ALL 4 learning points, PAUSE THE NARRATIVE and present a straightforward [QUIZ]
6. Quiz should test factual understanding of the 4 concepts covered
7. When user gets quiz right, the subtopic is mastered

CRITICAL RULES:
- Cover all 4 learning points in order, one scene per point
- Keep scenes concise (3-4 sentences max)
- ONE question per response, never multiple
- Stay focused on the learning points, no tangents
- After 4th learning point, STOP story and give quiz
- Use [MINI-Q] tag before every question (5-10 XP depending on depth)
- Use [QUIZ] tag for factual assessment question (difficulty: {quiz_difficulty}, 25 XP)
- After [QUIZ] is answered correctly, ask which subtopic to explore next

RESPONSE FORMAT FOR SCENES:
[Immersive scene describing the learning point]
[MINI-Q] One question about what the student sees/feels/predicts

RESPONSE FORMAT FOR QUIZ:
"We've experienced the story of [topic]. Let's test your understanding."
[QUIZ] [Straightforward factual question about covered concepts]

Tone: cinematic, engaging, focused for stories. Clear and direct for quizzes.
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
6. Quiz difficulty should match: {quiz_difficulty}
7. User must get 3/3 correct to master the subtopic
8. If they miss any, re-teach that specific point briefly and quiz again
9. When user gets 3/3, congratulate and ask which subtopic to explore next

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
[QUIZ] Question 1: [question about points 1-2 at {quiz_difficulty} difficulty]
(wait for answer and feedback)
[QUIZ] Question 2: [question about points 3-4 at {quiz_difficulty} difficulty]
(wait for answer and feedback)
[QUIZ] Question 3: [synthesis question across all points at {quiz_difficulty} difficulty]

Tone: friendly, clear, efficient. Give substantial explanations before moving on.
'''
}

INTRO_PROMPTS = {
    "Socratic": (
        "Welcome! I'll guide you through the Silk Road using the Socratic method. "
        "I'll teach you each concept first with clear information, then ask questions to help you think deeper about what we just learned. "
        "For each subtopic, I have 4 specific learning points to cover. Let's start with Origins & Expansion. "
        "Ready to begin?"
    ),
    "Narrative": (
        "Welcome! I'll teach you about the Silk Road through immersive stories and scenes. "
        "For each subtopic, I have 4 key learning points to cover through storytelling. "
        "You'll experience history firsthand through these narratives. Let's start with the first subtopic: Origins & Expansion. "
        "Ready to begin your journey?"
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
    return PERSONALITY_PROMPTS.get(personality, PERSONALITY_PROMPTS["Direct"])


def get_concept(key: Optional[str] = None):
    lookup = key or st.session_state.get("current_concept")
    for concept in LEARNING_CONCEPTS:
        if concept["key"] == lookup:
            return concept
    return LEARNING_CONCEPTS[0]


def update_learning_point_progress():
    """Update learning point progress based on recent conversation."""
    current_subtopic = st.session_state.get("current_subtopic")
    if not current_subtopic:
        return
    
    # Get the learning points for current subtopic
    learning_points = []
    for concept in LEARNING_CONCEPTS:
        for subtopic in concept.get("subtopics", []):
            if subtopic["key"] == current_subtopic:
                learning_points = subtopic.get("learning_points", [])
                break
    
    if not learning_points:
        return
    
    # Initialize if doesn't exist
    if "learning_point_progress" not in st.session_state:
        st.session_state.learning_point_progress = {}
    if current_subtopic not in st.session_state.learning_point_progress:
        st.session_state.learning_point_progress[current_subtopic] = {}
    
    # Get recent conversation text
    recent_messages = st.session_state.messages[-6:] if len(st.session_state.messages) >= 6 else st.session_state.messages
    conversation_text = " ".join([
        msg.content if isinstance(msg, Message) else (msg.get("content", "") if isinstance(msg, dict) else "")
        for msg in recent_messages if msg
    ]).lower()
    
    # Check which learning points have been discussed
    lp_progress = st.session_state.learning_point_progress[current_subtopic]
    
    for idx, point in enumerate(learning_points):
        lp_key = f"lp_{idx}"
        current_status = lp_progress.get(lp_key, "locked")
        
        # Extract key terms from learning point
        point_lower = point.lower()
        key_terms = []
        
        # Get distinctive words (longer than 4 chars, not common words)
        words = point_lower.split()
        for word in words:
            clean_word = word.strip('.,()[]{}":;!?')
            if len(clean_word) > 4 and clean_word not in ['about', 'their', 'which', 'where', 'these', 'those', 'through', 'between']:
                key_terms.append(clean_word)
        
        # Check if this learning point has been discussed
        matches = sum(1 for term in key_terms if term in conversation_text)
        
        if matches >= 2 and current_status != "completed":  # At least 2 key terms mentioned
            if current_status == "locked":
                lp_progress[lp_key] = "active"
            elif current_status == "active":
                # Mark as completed if discussed extensively
                recent_text = " ".join([
                    str(m.content) if isinstance(m, Message) else str(m.get("content", "")) if isinstance(m, dict) else ""
                    for m in recent_messages if m
                ])
                if matches >= 3 or "[MINI-Q]" in recent_text:
                    lp_progress[lp_key] = "completed"


def mark_subtopic_mastered(key: str):
    progress = st.session_state.subtopic_progress.get(key)
    if not progress:
        return
    if not progress["mastered"]:
        progress["mastered"] = True
        
        # Mark all learning points as completed
        if key in st.session_state.learning_point_progress:
            for lp_key in st.session_state.learning_point_progress[key]:
                st.session_state.learning_point_progress[key][lp_key] = "completed"
        
        # Unlock next subtopic
        subtopics = LEARNING_CONCEPTS[0]["subtopics"]
        index = next((idx for idx, s in enumerate(subtopics) if s["key"] == key), None)
        if index is not None and index + 1 < len(subtopics):
            next_key = subtopics[index + 1]["key"]
            unlock_subtopic(next_key)
            # Auto-switch to next subtopic
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
    
    if completed_count >= 3:  # 3 out of 4 learning points completed
        return "nearly_complete"
    elif completed_count >= 1:
        return "in_progress"
    else:
        return "not_started"


def select_bandit_action(action_type: str, context: Dict) -> str:
    """
    Epsilon-greedy contextual bandit selection.
    
    action_type: "hint_policy", "question_depth", or "quiz_difficulty"
    context: relevant state (user_level, subtopic_progress, time_of_day, etc.)
    """
    import random
    
    epsilon = 0.2  # 20% exploration, 80% exploitation
    
    bandit_stats = st.session_state.get("bandit_stats", {})
    
    if action_type == "hint_policy":
        actions = ["NO_AUTOMATIC_HINTS", "LIGHT_HINTS", "FULL_HINTS"]
        rewards_key = "hint_policy_rewards"
    elif action_type == "question_depth":
        actions = ["SHALLOW_CHECK", "DEEP_PROBE"]
        rewards_key = "depth_rewards"
    elif action_type == "quiz_difficulty":
        actions = ["EASY", "MEDIUM", "HARD"]
        rewards_key = "difficulty_rewards"
    else:
        return st.session_state.get(action_type, actions[0])
    
    # Epsilon-greedy: explore with probability epsilon
    if random.random() < epsilon:
        # Exploration: random action
        selected = random.choice(actions)
    else:
        # Exploitation: choose best action based on average reward
        avg_rewards = {}
        for action in actions:
            rewards = bandit_stats.get(rewards_key, {}).get(action, [])
            avg_rewards[action] = sum(rewards) / len(rewards) if rewards else 0.5  # Default to neutral
        
        # Select action with highest average reward
        selected = max(avg_rewards, key=avg_rewards.get)
    
    return selected


def record_bandit_reward(action_type: str, action: str, reward: float):
    """
    Record reward for a bandit action.
    
    reward: 0.0 to 1.0 (0 = worst, 1 = best)
    """
    bandit_stats = st.session_state.get("bandit_stats", {
        "hint_policy_rewards": {"NO_AUTOMATIC_HINTS": [], "LIGHT_HINTS": [], "FULL_HINTS": []},
        "depth_rewards": {"SHALLOW_CHECK": [], "DEEP_PROBE": []},
        "difficulty_rewards": {"EASY": [], "MEDIUM": [], "HARD": []},
    })
    
    if action_type == "hint_policy":
        rewards_key = "hint_policy_rewards"
    elif action_type == "question_depth":
        rewards_key = "depth_rewards"
    elif action_type == "quiz_difficulty":
        rewards_key = "difficulty_rewards"
    else:
        return
    
    if rewards_key not in bandit_stats:
        bandit_stats[rewards_key] = {}
    if action not in bandit_stats[rewards_key]:
        bandit_stats[rewards_key][action] = []
    
    bandit_stats[rewards_key][action].append(reward)
    
    # Keep only last 20 rewards to adapt to changing user behavior
    if len(bandit_stats[rewards_key][action]) > 20:
        bandit_stats[rewards_key][action] = bandit_stats[rewards_key][action][-20:]
    
    st.session_state.bandit_stats = bandit_stats
    save_persisted_state()


def check_learning_point_understanding():
    """
    Every ~3 turns for Socratic/Narrative, check if learner has understood current learning point.
    Updates visualization accordingly.
    """
    current_subtopic = st.session_state.get("current_subtopic")
    if not current_subtopic:
        return False
    
    # Get recent conversation
    recent_messages = st.session_state.messages[-6:] if len(st.session_state.messages) >= 6 else st.session_state.messages
    if len(recent_messages) < 4:  # Need at least 2 exchanges
        return False
    
    # Find which learning point we're currently on
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
    
    # Simple heuristic: if user has given 2+ substantive answers (6+ words each) since LP became active
    substantive_answers = 0
    for msg in recent_messages[-4:]:
        if isinstance(msg, Message) and msg.role == "user":
            if len(msg.content.split()) >= 6:
                substantive_answers += 1
    
    if substantive_answers >= 2:
        # Mark as completed
        lp_key = f"lp_{current_lp_idx}"
        lp_progress[lp_key] = "completed"
        
        # Activate next learning point if available
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

def build_tutor_context(personality: str, pdf_ref=None) -> str:
    # Get base personality prompt
    base_prompt = get_personality_prompt(personality)
    
    # Build adaptive instructions based on bandit selections
    quiz_difficulty = st.session_state.get("quiz_difficulty", "MEDIUM")
    
    if quiz_difficulty == "EASY":
        quiz_diff_instruction = "QUIZ DIFFICULTY: EASY - Ask straightforward recall questions with obvious answers. Example: 'What dynasty sent Zhang Qian to Central Asia?'"
    elif quiz_difficulty == "HARD":
        quiz_diff_instruction = "QUIZ DIFFICULTY: HARD - Ask synthesis questions requiring deep analysis and connections. Example: 'How did the geographic challenges of the Silk Road influence the types of goods that became most valuable?'"
    else:  # MEDIUM
        quiz_diff_instruction = "QUIZ DIFFICULTY: MEDIUM - Ask questions requiring understanding and application. Example: 'Why was controlling the Silk Road routes strategically important for the Han Dynasty?'"
    
    # For Socratic only: question depth and hint policy
    if personality == "Socratic":
        question_depth = st.session_state.get("question_depth", "DEEP_PROBE")
        hint_policy = st.session_state.get("hint_policy", "LIGHT_HINTS")
        
        if question_depth == "DEEP_PROBE":
            depth_instruction = "QUESTION DEPTH: DEEP - Ask at least 2 follow-up why/how questions about the same concept before moving to the next learning point. Probe deeper into reasoning."
        else:  # SHALLOW_CHECK
            depth_instruction = "QUESTION DEPTH: SHALLOW - Ask one quick understanding check per learning point, then advance if correct. Keep it efficient."
        
        if hint_policy == "NO_AUTOMATIC_HINTS":
            hint_instruction = "HINT POLICY: Only provide hints if student explicitly asks 'can I get a hint?' or similar."
        elif hint_policy == "FULL_HINTS":
            hint_instruction = "HINT POLICY: After one wrong or weak answer, provide a detailed scaffolded hint pointing toward the answer."
        else:  # LIGHT_HINTS
            hint_instruction = "HINT POLICY: After one wrong answer, give a small nudge ('Think about...') without giving away the answer."
        
        # Inject into template
        context = base_prompt.format(
            question_depth_instruction=depth_instruction,
            hint_policy_instruction=hint_instruction,
            quiz_difficulty_instruction=quiz_diff_instruction
        )
    else:
        # For Narrative and Direct, just inject quiz difficulty
        context = base_prompt.format(quiz_difficulty_instruction=quiz_diff_instruction)
    
    if personality == "Direct":
        context += "\n\nIMPORTANT: Only use [QUIZ] tags for the 3-question quiz at the end. Do not use [MINI-Q] tags."
    else:
        context += "\n\nIMPORTANT: Use [MINI-Q] and [QUIZ] tags. Keep responses concise."
    
    if personality == "Socratic":
        context += "\n- Award +10 XP when the student shows reasoning or cites evidence."
    elif personality == "Narrative":
        context += (
            "\n- Award +10 XP for historically accurate or empathetic responses and +5 XP for creative engagement."
        )
    else:
        context += "\n- Award 25 XP for each correct [QUIZ] answer. Students must get 3/3 to master the subtopic."
    
    # Add current subtopic learning points
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
            "\n\nCURRICULUM INTEGRATION: Use the uploaded PDF only as background knowledge. Summarise or paraphrase ideas in fresh language so the learner gets a self-contained explanation. Never quote the PDF verbatim. When a fact originated from the PDF, mention the page unobtrusively in parentheses (e.g., '(p. 4)') after your own explanation. The learner should not need to open the PDF to follow along."
        )
    active_concept = get_concept()
    if active_concept:
        context += (
            f"\n\nACTIVE CONCEPT: Focus on '{active_concept['title']}'. "
            f"Describe routes or decision points learners can choose between."
            f" Starter idea: {active_concept['description']}"
        )
    return context

def chat_with_tutor(model, personality: str, user_message: str, pdf_ref=None) -> str:
    try:
        pdf_id = getattr(pdf_ref, "name", None) or getattr(pdf_ref, "uri", None)
        chat = st.session_state.get("chat_session")
        needs_reset = (
            chat is None
            or st.session_state.get("chat_session_personality") != personality
            or st.session_state.get("chat_session_pdf_id") != pdf_id
        )

        if needs_reset:
            system_context = build_tutor_context(personality, pdf_ref)
            chat_history = [{"role": "user", "parts": [system_context]}]
            chat = model.start_chat(history=chat_history)
            st.session_state.chat_session = chat
            st.session_state.chat_session_personality = personality
            st.session_state.chat_session_pdf_id = pdf_id

        if pdf_ref:
            response = chat.send_message([user_message, pdf_ref])
        else:
            response = chat.send_message(user_message)

        return getattr(response, "text", "") or ""
    except Exception as e:
        st.session_state.chat_session = None
        return f"(Error: {e})"

def parse_tutor_response(response: str):
    question_type = None
    
    # Check for explicit tags first
    if "[MINI-Q]" in response:
        question_type = "mini"
        response = response.replace("[MINI-Q]", "**Mini-Question:**")
    elif "[QUIZ]" in response:
        question_type = "quiz"
        response = response.replace("[QUIZ]", "**Quiz:**")
    # If no tags but mentions "+10 XP" or similar, treat as mini question
    elif ("+10 XP" in response or "+10XP" in response or "+ 10 XP" in response):
        question_type = "mini"
        # Add the tag indicator
        if "?" in response:  # Contains a question
            response = "**Mini-Question:** " + response
    elif ("+5 XP" in response or "+5XP" in response):
        question_type = "mini"
        if "?" in response:
            response = "**Mini-Question:** " + response
    
    return response, question_type


def ensure_initial_tutor_message(model):
    if st.session_state.intro_sent:
        return
    if st.session_state.messages:
        st.session_state.intro_sent = True
        return
    if model is None:
        return

    personality = st.session_state.personality
    prompt = INTRO_PROMPTS.get(personality, INTRO_PROMPTS["Direct"])

    with st.spinner("Tutor is getting ready..."):
        reply = chat_with_tutor(
            model,
            personality,
            prompt,
            st.session_state.pdf_file_ref,
        )

    clean_reply, question_type = parse_tutor_response(reply)

    st.session_state.messages.append(
        Message(role="assistant", content=clean_reply, metadata={"question_type": question_type})
    )

    if question_type:
        st.session_state.awaiting_answer = True
        st.session_state.question_type = question_type

    st.session_state.intro_sent = True

def check_answer_quality(user_answer: str, question_type: str, personality: str):
    words = user_answer.strip().split()
    if len(words) < 2:
        return False, 0, ""

    # For Direct personality, all questions are quizzes worth 25 XP
    if personality == "Direct" and question_type == "quiz":
        # Track quiz progress
        if not st.session_state.get("quiz_mode"):
            st.session_state.quiz_mode = True
            st.session_state.quiz_score = 0
            st.session_state.quiz_total = 0
        
        # Simple validation - if answer is substantive, consider it valid
        # The tutor AI will determine correctness
        if len(words) >= 3:
            return True, 25, "Quiz question"
        return False, 0, ""
    
    # Standard quiz reward for other personalities
    if question_type == "quiz":
        return True, 25, "Quiz mastery"

    lower_answer = user_answer.lower()
    word_count = len(words)
    cleaned = " ".join(lower_answer.split()).strip()
    exact_invalid = {
        "idk",
        "i don't know",
        "i dont know",
        "no idea",
        "not sure",
        "no clue",
        "?",
        "??",
        "???",
    }
    substring_invalid = {
        "i don't know",
        "i dont know",
        "dont know",
        "don't know",
    }
    if cleaned in exact_invalid or any(sub in cleaned for sub in substring_invalid):
        return False, 0, ""

    if personality == "Socratic":
        # Socratic questions are about thinking, not memorization
        # Any thoughtful response (6+ words) should be rewarded
        if word_count >= 6:
            return True, 10, "Thoughtful response"
        return False, 0, ""

    if personality == "Narrative":
        empathy_keywords = {
            "feel", "felt", "think", "imagine", "because", "worried", "afraid", "hope", "angry", "tired"
        }
        if word_count >= 12 or any(keyword in lower_answer for keyword in empathy_keywords):
            return True, 10, "Insightful historical perspective"
        return True, 5, "Creative engagement"

    # Should not reach here for Direct personality
    return False, 0, ""

def render_concept_tracker():
    concept = LEARNING_CONCEPTS[0]  # Silk Road only
    
    st.markdown(f"**{concept['title']}**")
    
    for subtopic in concept["subtopics"]:
        key = subtopic["key"]
        # Check session state for this subtopic's progress
        progress = st.session_state.get("subtopic_progress", {}).get(key, {
            "unlocked": subtopic.get("unlocked", False),
            "mastered": subtopic.get("mastered", False)
        })
        
        is_current = key == st.session_state.get("current_subtopic")
        
        # Determine subtopic-level status
        if progress.get("mastered"):
            state_class = "concept-chip mastered"
            icon = "●"
            color = "green"
        elif is_current:
            state_class = "concept-chip active"
            icon = "●"
            color = "yellow"
        elif not progress.get("unlocked"):
            state_class = "concept-chip locked"
            icon = "●"
            color = "gray"
        else:
            state_class = "concept-chip available"
            icon = "●"
            color = "blue"
        
        # Subtopic title
        label = f"<span style='color: {color};'>{icon}</span> <strong>{subtopic['title']}</strong>"
        st.markdown(f"<div class='{state_class}'>{label}</div>", unsafe_allow_html=True)
        
        # Show learning points if unlocked or current
        if progress.get("unlocked") or is_current:
            learning_points = subtopic.get("learning_points", [])
            if learning_points:
                # Get individual learning point progress from session state
                lp_progress = st.session_state.get("learning_point_progress", {}).get(key, {})
                
                for idx, point in enumerate(learning_points):
                    lp_key = f"lp_{idx}"
                    lp_status = lp_progress.get(lp_key, "locked")  # locked, active, completed
                    
                    if lp_status == "completed":
                        lp_icon = "●"
                        lp_color = "green"
                    elif lp_status == "active":
                        lp_icon = "●"
                        lp_color = "yellow"
                    else:
                        lp_icon = "●"
                        lp_color = "lightgray"
                    
                    # Truncate long learning points for display
                    display_point = point if len(point) <= 50 else point[:47] + "..."
                    lp_html = f"<div style='margin-left: 1.5em; font-size: 0.85em; color: #555; margin-top: 0.3em;'><span style='color: {lp_color};'>{lp_icon}</span> {display_point}</div>"
                    st.markdown(lp_html, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-bottom: 0.8em;'></div>", unsafe_allow_html=True)

def sidebar_nav():
    with st.sidebar:
        st.markdown("## TutorQuest")
        username = st.session_state.get("username", "Guest")
        st.caption(f"Welcome, **{username}**!")
        
        # Navigation buttons
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
            st.markdown("### Tutor Personality")
            personalities = ["Socratic", "Narrative", "Direct"]
            if st.session_state.personality not in personalities:
                st.session_state.personality = "Socratic"
            
            descriptions = {
                "Socratic": "Guides you with layered questions",
                "Narrative": "Immerses you in historical stories",
                "Direct": "Delivers clear, structured lessons"
            }
            
            # Use buttons instead of selectbox for personality
            for p in personalities:
                is_active = st.session_state.personality == p
                button_type = "primary" if is_active else "secondary"
                if st.button(f"{p}", use_container_width=True, type=button_type, key=f"personality_{p}"):
                    if p != st.session_state.personality:
                        st.session_state.personality = p
                        st.session_state.chat_session = None
                        st.session_state.chat_session_personality = None
                        st.session_state.chat_session_pdf_id = None
                        st.session_state.messages = []
                        st.session_state.awaiting_answer = False
                        st.session_state.question_type = None
                        st.session_state.current_topic = "General Tutoring"
                        st.session_state.intro_sent = False
                        save_persisted_state()
                        st.rerun()
            
            st.caption(descriptions[st.session_state.personality])
            st.divider()
        
        st.metric("Level", st.session_state.level)
        st.metric("XP", st.session_state.xp)
        st.progress(level_progress(st.session_state.xp))
        st.markdown("### Silk Road Progress")
        render_concept_tracker()
        
        st.divider()
        
        # Export chat history
        if len(st.session_state.messages) > 0:
            chat_export = []
            for msg in st.session_state.messages:
                if isinstance(msg, Message):
                    chat_export.append({
                        "role": msg.role,
                        "content": msg.content
                    })
                elif isinstance(msg, dict):
                    chat_export.append({
                        "role": msg.get("role", "unknown"),
                        "content": msg.get("content", "")
                    })
            
            import json
            chat_json = json.dumps(chat_export, indent=2)
            
            st.download_button(
                label="Download Chat History",
                data=chat_json,
                file_name=f"silk_road_chat_{st.session_state.current_subtopic}.json",
                mime="application/json",
                use_container_width=True
            )
        
        st.divider()
        
        # User card at bottom
        with st.container(border=True):
            st.markdown("#### Profile")
            username = st.session_state.get("username", "Guest")
            st.markdown(f"**{username}**")
            st.caption(f"Level {st.session_state.level} • {st.session_state.xp} XP")
            if st.button("Sign Out", use_container_width=True, type="secondary"):
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
            questions_total = len([m for m in st.session_state.messages if m.role == "user"])
            mini_qs = len([
                m
                for m in st.session_state.messages
                if hasattr(m, "metadata") and m.metadata and m.metadata.get("type") == "mini"
            ])
            quizzes = len([
                m
                for m in st.session_state.messages
                if hasattr(m, "metadata") and m.metadata and m.metadata.get("type") == "quiz"
            ])
            s1, s2, s3 = st.columns(3)
            s1.metric("Questions", questions_total)
            s2.metric("Mini-Qs", mini_qs)
            s3.metric("Quizzes", quizzes)

    with col_side:
        with st.container(border=True):
            st.subheader("Badges")
            badges = ["Starter"]
            if st.session_state.level >= 2:
                badges.append("Focused Learner")
            if st.session_state.level >= 5:
                badges.append("Knowledge Seeker")
            st.write("\n".join(badges))
        st.markdown("\n")
        with st.container(border=True):
            st.subheader("Next goals")
            st.markdown("- Complete a tutor chat\n- Answer a Mini-Q\n- Finish a quiz round")

    st.markdown("---")
    st.subheader("Daily actions")
    st.caption("Use these quick actions to keep your streak alive and unlock bonuses.")
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        if st.button("Practice +15 XP", use_container_width=True, type="primary"):
            award_xp(15, "Practice completed")
    with a2:
        if st.button("Lesson +30 XP", use_container_width=True):
            award_xp(30, "Lesson completed")
    with a3:
        if st.button("Streak +10 XP", use_container_width=True):
            award_xp(10, "Streak maintained")
    with a4:
        if st.button("Challenge Question", use_container_width=True, help="Navigate to tutor and receive a tough question for bonus XP"):
            st.session_state.page = "Tutoring Chat"
            st.session_state.challenge_active = True
            st.toast("Challenge armed! Head to Tutoring Chat to get your tough question.", icon="⚡")
            save_persisted_state()
            st.rerun()

    st.info("Tip: Chat with your AI tutor and answer questions to earn XP!")

def page_chat():
    st.title("Tutoring Chat")
    st.caption(f"Learning with **{st.session_state.personality}** tutor • Answer questions to earn XP")
    st.markdown(f"**Current Topic:** {st.session_state.current_topic}")

    model = get_gemini_model()
    if model is None:
        st.error("Gemini API key not configured.")
        return

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
                    save_persisted_state()
                    st.success(f"PDF uploaded: {uploaded_file.name}")
                    st.rerun()
    
    local_pdf = Path("/Users/alishajain/Gamified_app/Unit 2_ 2.1-2.7.pdf")
    if local_pdf.exists() and not st.session_state.pdf_uploaded:
        if st.button("Load Unit 2 Curriculum (2.1-2.7)"):
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
            # Immediately send challenge prompt
            challenge_prompt = "Give me a challenge question on everything we've discussed in this chat so far. This should test deep synthesis and understanding across multiple concepts."
            
            st.session_state.messages.append(
                Message(role="user", content=challenge_prompt, metadata=None)
            )
            save_persisted_state()
            
            with st.spinner("Preparing challenge question..."):
                reply = chat_with_tutor(
                    model,
                    st.session_state.personality,
                    challenge_prompt,
                    st.session_state.pdf_file_ref
                )
            
            clean_reply, question_type = parse_tutor_response(reply)
            
            st.session_state.messages.append(
                Message(role="assistant", content=clean_reply, metadata={"question_type": question_type})
            )
            
            st.session_state.awaiting_answer = True
            st.session_state.question_type = question_type or "quiz"
            st.session_state.challenge_active = True
            save_persisted_state()
            st.rerun()

    st.markdown("##### Quick starts:")
    pp1, pp2, pp3, pp4 = st.columns([1.4, 1.6, 1.8, 2])
    
    quick_starts = {
        "Socratic": [
            ("Northern Route", "Guide me through the northern Silk Road route with questions."),
            ("Trade Goods", "Help me reason through what goods were traded on the Silk Road."),
            ("Cultural Exchange", "Ask me guiding questions about cultural exchange on the Silk Road.")
        ],
        "Narrative": [
            ("Merchant's Journey", "Put me in a merchant's caravan traveling the Silk Road."),
            ("Desert Oasis", "Tell the story of arriving at a Silk Road desert oasis."),
            ("Cultural Meeting", "Let me experience a cultural exchange moment on the Silk Road.")
        ],
        "Direct": [
            ("Silk Road Origins", "Teach me about the origins and expansion of the Silk Road."),
            ("Route Comparison", "Walk me through the northern vs. southern Silk Road routes."),
            ("Political Powers", "Give me a clear outline of empires controlling the Silk Road.")
        ]
    }
    
    starts = quick_starts.get(st.session_state.personality, quick_starts["Direct"])
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
    
    ensure_initial_tutor_message(model)

    with st.container(border=True):
        for idx, m in enumerate(st.session_state.messages):
            # Handle both dict and Message object formats
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
                                "Edit message",
                                value=content,
                                key=f"edit_{idx}",
                                label_visibility="collapsed"
                            )
                            if st.button("Save", key=f"save_{idx}"):
                                # Update the message
                                if isinstance(st.session_state.messages[idx], dict):
                                    st.session_state.messages[idx]["content"] = edited_text
                                else:
                                    st.session_state.messages[idx].content = edited_text
                                st.session_state.editing_message_idx = None
                                
                                # Remove all messages after this one
                                st.session_state.messages = st.session_state.messages[:idx+1]
                                
                                # Re-prompt the model with the edited message
                                with st.spinner("Tutor is thinking..."):
                                    reply = chat_with_tutor(
                                        model,
                                        st.session_state.personality,
                                        edited_text,
                                        st.session_state.pdf_file_ref
                                    )
                                
                                clean_reply, question_type = parse_tutor_response(reply)
                                
                                st.session_state.messages.append(
                                    Message(role="assistant", content=clean_reply, metadata={"question_type": question_type})
                                )
                                
                                if question_type:
                                    st.session_state.awaiting_answer = True
                                    st.session_state.question_type = question_type
                                
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
                    st.markdown(content)

    user_input = st.chat_input("Ask a question or answer the tutor...")
    query = chip_query or user_input
    
    if query:
        topic_update = None
        if chip_topic:
            topic_update = chip_topic
        elif user_input and not st.session_state.awaiting_answer:
            topic_update = user_input.strip()

        st.session_state.messages.append(
            Message(role="user", content=query, metadata=None)
        )
        save_persisted_state()

        pending_type = st.session_state.question_type
        if st.session_state.awaiting_answer and pending_type:
            # Calculate response time
            import time
            current_time = time.time()
            response_time = current_time - st.session_state.get("last_question_time", current_time)
            
            is_valid, xp, reason = check_answer_quality(
                query, pending_type, st.session_state.personality
            )
            
            # Record bandit rewards
            if pending_type == "quiz":
                # Quiz difficulty reward
                if response_time < 120 and is_valid and xp > 0:  # < 2 minutes, correct
                    difficulty_reward = 1.0
                elif response_time < 120 and not is_valid:  # < 2 minutes, incorrect (too hard?)
                    difficulty_reward = 0.3
                else:  # > 2 minutes (timeout or disengaged)
                    difficulty_reward = 0.0 if response_time > 180 else 0.5
                
                record_bandit_reward("quiz_difficulty", st.session_state.get("quiz_difficulty", "MEDIUM"), difficulty_reward)
                
                # Re-select difficulty for next quiz
                context = {"user_level": st.session_state.level, "xp": st.session_state.xp}
                st.session_state.quiz_difficulty = select_bandit_action("quiz_difficulty", context)
            
            # For Socratic: track hint policy and question depth rewards
            if st.session_state.personality == "Socratic":
                # Depth reward: good if answered correctly and not too slow
                if is_valid and xp > 0:
                    if response_time < 90:
                        depth_reward = 1.0  # Quick and correct
                    elif response_time < 180:
                        depth_reward = 0.7  # Correct but slow
                    else:
                        depth_reward = 0.4  # Very slow
                elif "idk" not in query.lower() and "don't know" not in query.lower():
                    depth_reward = 0.4  # Trying but incorrect
                else:
                    depth_reward = 0.1  # Gave up
                
                record_bandit_reward("question_depth", st.session_state.get("question_depth", "DEEP_PROBE"), depth_reward)
                
                # Re-select for next question
                context = {"engagement": depth_reward, "level": st.session_state.level}
                st.session_state.question_depth = select_bandit_action("question_depth", context)
            
            if is_valid and xp > 0:
                award_xp(xp, reason or f"{pending_type.title()} response")
                metadata = {
                    "type": pending_type,
                    "xp_awarded": xp,
                    "reason": reason,
                    "personality": st.session_state.personality,
                    "response_time": response_time,
                }
                if st.session_state.challenge_active:
                    award_xp(10, "Challenge bonus")
                    metadata["challenge_bonus"] = 10
                    st.session_state.challenge_active = False
                if pending_type == "quiz":
                    mark_subtopic_mastered(st.session_state.current_subtopic)
                st.session_state.messages[-1].metadata = metadata
                save_persisted_state()
            else:
                if st.session_state.challenge_active:
                    st.toast("Challenge bonus still waiting for a strong answer.", icon="⌛")
            st.session_state.awaiting_answer = False
            st.session_state.question_type = None
        elif topic_update:
            concept_key = st.session_state.current_concept
            st.session_state.current_topic = derive_topic_label(topic_update, concept_key)
            st.session_state.topic_refresh_counter = 0
            save_persisted_state()

        with st.spinner("Tutor is thinking..."):
            reply = chat_with_tutor(
                model,
                st.session_state.personality,
                query,
                st.session_state.pdf_file_ref
            )

        clean_reply, question_type = parse_tutor_response(reply)
        
        st.session_state.messages.append(
            Message(role="assistant", content=clean_reply, metadata={"question_type": question_type})
        )
        refresh_topic_periodically()
        
        # Update learning point progress
        st.session_state.message_count_for_lp_update += 1
        personality = st.session_state.personality
        
        # For Direct, update after quiz completion
        if personality == "Direct" and question_type == "quiz":
            update_learning_point_progress()
        # For Socratic/Narrative, update every 3 messages
        elif personality in ["Socratic", "Narrative"] and st.session_state.message_count_for_lp_update >= 3:
            update_learning_point_progress()
            st.session_state.message_count_for_lp_update = 0
            # Also check if current learning point is understood
            if check_learning_point_understanding():
                st.toast("Learning point mastered!", icon="✓")
        
        save_persisted_state()
        
        if question_type:
            st.session_state.awaiting_answer = True
            st.session_state.question_type = question_type
            # Record question start time for bandit timeout tracking
            import time
            st.session_state.last_question_time = time.time()
            
            # Select adaptive settings before next question (for display)
            if question_type == "quiz":
                context = {"level": st.session_state.level, "xp": st.session_state.xp}
                st.session_state.quiz_difficulty = select_bandit_action("quiz_difficulty", context)
        
        st.rerun()

    # Bottom section with Continue buttons for Direct, Reset, and status
    if st.session_state.personality == "Direct" and len(st.session_state.messages) > 1:
        # Show Continue/Quiz buttons for Direct personality
        col_cont1, col_cont2, col_cont3 = st.columns([1, 1, 1])
        with col_cont1:
            if st.button("Continue", use_container_width=True, type="primary", key="continue_btn_bottom"):
                query = "continue"
                st.session_state.messages.append(Message(role="user", content=query, metadata=None))
                save_persisted_state()
                with st.spinner("Tutor is thinking..."):
                    reply = chat_with_tutor(model, st.session_state.personality, query, st.session_state.pdf_file_ref)
                clean_reply, question_type = parse_tutor_response(reply)
                st.session_state.messages.append(Message(role="assistant", content=clean_reply, metadata={"question_type": question_type}))
                if question_type:
                    st.session_state.awaiting_answer = True
                    st.session_state.question_type = question_type
                save_persisted_state()
                st.rerun()
        with col_cont2:
            if st.button("Ready for Quiz", use_container_width=True, key="quiz_btn_bottom"):
                query = "I'm ready for the quiz"
                st.session_state.messages.append(Message(role="user", content=query, metadata=None))
                save_persisted_state()
                with st.spinner("Preparing quiz..."):
                    reply = chat_with_tutor(model, st.session_state.personality, query, st.session_state.pdf_file_ref)
                clean_reply, question_type = parse_tutor_response(reply)
                st.session_state.messages.append(Message(role="assistant", content=clean_reply, metadata={"question_type": question_type}))
                if question_type:
                    st.session_state.awaiting_answer = True
                    st.session_state.question_type = question_type
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
                save_persisted_state()
                st.rerun()
    else:
        # Regular Reset button for non-Direct personalities
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
                save_persisted_state()
                st.rerun()
        with col_b:
            if st.session_state.awaiting_answer:
                q_type = st.session_state.question_type
                if q_type == "mini":
                    personality = st.session_state.personality
                    if personality == "Socratic":
                        xp_label = "10 XP for strong reasoning"
                    elif personality == "Narrative":
                        xp_label = "5-10 XP for story insight"
                else:
                    xp_label = "25 XP for quiz question"
                st.info(f"Awaiting answer • {xp_label}")
            else:
                if st.session_state.challenge_active:
                    st.caption("Challenge armed: next correct answer earns +10 bonus XP on top of regular rewards.")
                else:
                    st.caption("Socratic Mini-Q: 10 XP • Narrative Mini-Q: 5-10 XP • Direct Quiz: 25 XP per question")
    
    # Status line for Direct
    if st.session_state.personality == "Direct":
        if st.session_state.awaiting_answer:
            st.info(f"Awaiting quiz answer • 25 XP per correct answer")
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
            st.session_state.user_id = user_id
            st.session_state.username = username.strip()
            st.session_state.db_state_loaded = False  # Mark as needing to load
            save_persisted_state()  # Save login state immediately
            st.success("Signed in successfully")
            st.rerun()
        else:
            st.error("Invalid username or password.")
    
    if register and username and password:
        created = db.create_user(username.strip(), password)
        if created:
            st.session_state.user_id = created
            st.session_state.username = username.strip()
            st.session_state.db_state_loaded = False
            save_persisted_state()  # Save login state immediately
            st.success("Account created and signed in.")
            st.rerun()
        else:
            st.error("Could not create account (username may already exist).")

def main():
    st.set_page_config(
        page_title="TutorQuest",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    # ensure DB exists
    try:
        db.init_db()
    except Exception as e:
        st.error(f"Database initialization failed: {e}")
    
    init_state()
    apply_styles()

    # If user is not signed in, show login/register page
    if not st.session_state.get("user_id"):
        show_login_page()
        return

    # If logged in and DB has stored state, load it once
    if st.session_state.get("user_id") and not st.session_state.get("db_state_loaded"):
        try:
            state = db.get_user_state(st.session_state["user_id"])
            if isinstance(state, dict):
                # Load messages properly as Message objects
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
                
                # Load other state
                for k, v in state.items():
                    if k == "messages":
                        continue  # Already handled above
                    if k in ("xp", "level", "concept_progress", "subtopic_progress", "learning_point_progress", "current_concept", "current_subtopic", "current_topic", "personality", "challenge_active"):
                        st.session_state[k] = v
                
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