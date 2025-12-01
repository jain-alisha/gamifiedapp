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
                "mastered": False
            },
            {
                "key": "northern_route",
                "title": "Northern Route",
                "description": "Through Central Asia and the steppes",
                "unlocked": False,
                "mastered": False
            },
            {
                "key": "southern_route",
                "title": "Southern Route",
                "description": "Through the oases and deserts",
                "unlocked": False,
                "mastered": False
            },
            {
                "key": "goods_trade",
                "title": "Goods & Trade",
                "description": "Silk, spices, jade, and more",
                "unlocked": False,
                "mastered": False
            },
            {
                "key": "cultural_exchange",
                "title": "Cultural Exchange",
                "description": "Ideas, religions, and technologies",
                "unlocked": False,
                "mastered": False
            },
            {
                "key": "political_powers",
                "title": "Political Powers",
                "description": "Empires controlling the routes",
                "unlocked": False,
                "mastered": False
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
        "current_concept": st.session_state.get("current_concept"),
        "current_subtopic": st.session_state.get("current_subtopic"),
        "current_topic": st.session_state.get("current_topic"),
        "personality": st.session_state.get("personality"),
        "challenge_active": st.session_state.get("challenge_active", False),
        "messages": messages_payload,
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
    for subtopic in LEARNING_CONCEPTS[0]["subtopics"]:
        default_subtopic_progress[subtopic["key"]] = {
            "unlocked": subtopic.get("unlocked", False),
            "mastered": subtopic.get("mastered", False),
        }
    
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
        "community_pointer": 0,
        "challenge_active": persisted.get("challenge_active", False),
        "topic_refresh_counter": 0,
        "editing_message_idx": None,
        "db_state_loaded": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
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

Always:
- Begin each new topic with a concise primer (1–2 key facts) before asking the first question, so learners who have not seen the material can engage.
- Ask open-ended, thought-provoking questions ("Why do you think ...?", "What evidence supports that?").
- Build on the student's answers, going one layer deeper each time, and provide scaffolding or hints if they seem unsure.
- Reference historical context to ground the discussion without delivering long lectures.
- Reward reasoning supported by evidence with +10 XP and brief positive feedback.
- After three to four guided questions, summarise what the student reasoned correctly and encourage reflection.
- When challenge mode is activated, present a difficult [QUIZ] question that requires synthesis and deep understanding.

If the learner says they do not know, offer a short explanation or hint, then follow up with a simpler question.

Tone: respectful, curious, mentor-like. Guide discovery step-by-step.

Tagging rules:
- Use [MINI-Q] before learning checkpoint questions worth 10 XP.
- Use [QUIZ] before mastery questions that validate understanding (25 XP).
- Challenge questions should always be [QUIZ] tagged.
''',

    "Narrative": '''You are a narrative-style history tutor who teaches through immersive storytelling and historical role-play.

Always:
- Frame each topic as a short scene or chapter with time, place, and emotion.
- Give the student a role inside the story and ask what they see, feel, or predict.
- Reward thoughtful or empathetic responses with XP (+10 XP for accurate historical insight, +5 XP for creative engagement).
- Reveal what actually happened and explain its significance after the student responds.
- Keep story segments to three to five interactions, then recap key facts.
- When challenge mode is activated, present a difficult scenario-based [QUIZ] question that tests deep contextual understanding.

Tone: cinematic, engaging, vivid. Avoid dry fact lists.

Tagging rules:
- Use [MINI-Q] for in-story checkpoints (award 5–10 XP depending on depth of response).
- Use [QUIZ] for short end-of-story quizzes (25 XP for correct answers).
- Challenge questions should always be [QUIZ] tagged.
''',

    "Direct": '''You are a direct, structured history tutor who delivers curriculum-aligned lessons clearly and efficiently.

Always:
- Start with an overview of the lesson objective.
- Present concise factual content in short chunks.
- After each chunk, ask a quick comprehension check tagged with [MINI-Q] and award +15 XP for correct answers.
- Provide immediate, friendly feedback and short corrections, including optional hints.
- End each topic with a three to five question [QUIZ] that reinforces key facts, award 25 XP for correct answers, and highlight module completion.
- When challenge mode is activated, present a comprehensive [QUIZ] question that requires synthesis across multiple concepts.

Tone: friendly, clear, supportive — like a teacher reviewing notes alongside the student.

Tagging rules:
- Use [MINI-Q] for comprehension checks worth 15 XP.
- Use [QUIZ] for mastery assessments worth 25 XP.
- Challenge questions should always be [QUIZ] tagged.
'''
}

INTRO_PROMPTS = {
    "Socratic": (
        "Introduce yourself warmly, give a short primer (2-3 sentences) on an accessible history topic "
        "of your choice, and explain the key idea so a learner without prior reading can follow. Ask "
        "what part they would like to explore next. Do not include [MINI-Q] or [QUIZ] tags yet."
    ),
    "Narrative": (
        "Greet the learner and drop them into a brief story scene that teaches an important history "
        "moment. Provide the essential context in a few sentences and invite them to choose what to "
        "experience or understand next. Avoid [MINI-Q] or [QUIZ] tags in this welcome."
    ),
    "Direct": (
        "Welcome the learner, state today's objective in clear terms, outline the core points you will "
        "cover, and ask which subtopic they want to tackle first. Hold off on [MINI-Q] and [QUIZ] tags "
        "until after they reply."
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


def unlock_subtopic(key: str):
    progress = st.session_state.subtopic_progress.setdefault(key, {"unlocked": False, "mastered": False})
    if not progress["unlocked"]:
        progress["unlocked"] = True
        save_persisted_state()


def mark_subtopic_mastered(key: str):
    progress = st.session_state.subtopic_progress.get(key)
    if not progress:
        return
    if not progress["mastered"]:
        progress["mastered"] = True
        # Unlock next subtopic
        subtopics = LEARNING_CONCEPTS[0]["subtopics"]
        index = next((idx for idx, s in enumerate(subtopics) if s["key"] == key), None)
        if index is not None and index + 1 < len(subtopics):
            next_key = subtopics[index + 1]["key"]
            unlock_subtopic(next_key)
            st.toast("New subtopic unlocked!", icon="🚀")
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
    context = get_personality_prompt(personality)
    context += "\n\nIMPORTANT: Use [MINI-Q] and [QUIZ] tags. Keep responses concise."
    if personality == "Socratic":
        context += "\n- Award +10 XP when the student shows reasoning or cites evidence."
    elif personality == "Narrative":
        context += (
            "\n- Award +10 XP for historically accurate or empathetic responses and +5 XP for creative engagement."
        )
    else:
        context += "\n- Award +15 XP for correct recall on [MINI-Q] checks and 25 XP for [QUIZ] mastery."
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
    if "[MINI-Q]" in response:
        question_type = "mini"
        response = response.replace("[MINI-Q]", "🤔 **Mini-Question:**")
    elif "[QUIZ]" in response:
        question_type = "quiz"
        response = response.replace("[QUIZ]", "📝 **Quiz:**")
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
    concept = get_concept()
    prompt += (
        f"\n\nActive concept: {concept['title']}. "
        f"Offer two to three learning routes the student can choose from related to {concept['description']}"
        " and invite them to pick one."
    )

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

    # Standard quiz reward regardless of personality
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
        reasoning_keywords = {
            "because", "since", "due", "therefore", "reason", "cause", "led", "result", "impact"
        }
        if word_count >= 8 and any(keyword in lower_answer for keyword in reasoning_keywords):
            return True, 10, "Evidence-based reasoning"
        if word_count >= 12:
            return True, 10, "Thoughtful reflection"
        return False, 0, ""

    if personality == "Narrative":
        empathy_keywords = {
            "feel", "felt", "think", "imagine", "because", "worried", "afraid", "hope", "angry", "tired"
        }
        if word_count >= 12 or any(keyword in lower_answer for keyword in empathy_keywords):
            return True, 10, "Insightful historical perspective"
        return True, 5, "Creative engagement"

    # Direct / default
    if word_count >= 4:
        return True, 15, "Accurate recall"
    return False, 0, ""

def render_concept_tracker():
    items_html = []
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
        
        if progress.get("mastered"):
            state_class = "concept-chip mastered"
            icon = "🟢"
        elif is_current:
            state_class = "concept-chip active"
            icon = "🟡"
        elif not progress.get("unlocked"):
            state_class = "concept-chip locked"
            icon = "⚫"
        else:
            state_class = "concept-chip available"
            icon = "🔵"
        
        label = f"{icon} {subtopic['title']}"
        desc = f"<div style='font-size: 0.8em; color: #666; margin-left: 1.5em;'>{subtopic['description']}</div>"
        items_html.append(f"<div class='{state_class}'>{label}</div>{desc}")
    
    tracker_html = "".join(items_html)
    st.markdown(f"<div class='concept-tracker'>{tracker_html}</div>", unsafe_allow_html=True)

def sidebar_nav():
    with st.sidebar:
        st.markdown("## 🎓 TutorQuest")
        username = st.session_state.get("username", "Guest")
        st.caption(f"Welcome, **{username}**!")
        
        # Navigation buttons
        st.markdown("### Navigate")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏠 Home", use_container_width=True, type="primary" if st.session_state.page == "User Home" else "secondary"):
                st.session_state.page = "User Home"
                st.rerun()
        with col2:
            if st.button("💬 Chat", use_container_width=True, type="primary" if st.session_state.page == "Tutoring Chat" else "secondary"):
                st.session_state.page = "Tutoring Chat"
                st.rerun()
        
        st.divider()
        
        if st.session_state.page == "Tutoring Chat":
            st.markdown("### Tutor Personality")
            personalities = ["Socratic", "Narrative", "Direct"]
            if st.session_state.personality not in personalities:
                st.session_state.personality = "Socratic"
            
            descriptions = {
                "Socratic": "📚 Guides you with layered questions",
                "Narrative": "📖 Immerses you in historical stories",
                "Direct": "🎯 Delivers clear, structured lessons"
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
        
        # User card at bottom
        with st.container(border=True):
            st.markdown("#### 👤 Profile")
            username = st.session_state.get("username", "Guest")
            st.markdown(f"**{username}**")
            st.caption(f"Level {st.session_state.level} • {st.session_state.xp} XP")
            if st.button("Sign Out", use_container_width=True, type="secondary"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

def page_home():
    st.title("Welcome back 👋")
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
            badges = ["🏅 Starter"]
            if st.session_state.level >= 2:
                badges.append("🎯 Focused Learner")
            if st.session_state.level >= 5:
                badges.append("🔥 Knowledge Seeker")
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
        if st.button("🧠 Practice +15 XP", use_container_width=True, type="primary"):
            award_xp(15, "Practice completed")
    with a2:
        if st.button("📘 Lesson +30 XP", use_container_width=True):
            award_xp(30, "Lesson completed")
    with a3:
        if st.button("🔥 Streak +10 XP", use_container_width=True):
            award_xp(10, "Streak maintained")
    with a4:
        if st.button("⚔️ Challenge Question", use_container_width=True, help="Navigate to tutor and receive a tough question for bonus XP"):
            st.session_state.page = "Tutoring Chat"
            st.session_state.challenge_active = True
            st.toast("Challenge armed! Head to Tutoring Chat to get your tough question.", icon="⚡")
            save_persisted_state()
            st.rerun()

    st.info("💡 **Tip:** Chat with your AI tutor and answer questions to earn XP!")

def page_chat():
    st.title("Tutoring Chat 💬")
    st.caption(f"Learning with **{st.session_state.personality}** tutor • Answer questions to earn XP")
    st.markdown(f"**Current Topic:** {st.session_state.current_topic}")

    model = get_gemini_model()
    if model is None:
        st.error("⚠️ Gemini API key not configured.")
        return

    with st.expander("📄 Upload Curriculum (PDF)", expanded=not st.session_state.pdf_uploaded):
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
                    st.success(f"✅ PDF uploaded: {uploaded_file.name}")
                    st.rerun()
    
    local_pdf = Path("/Users/alishajain/Gamified_app/Unit 2_ 2.1-2.7.pdf")
    if local_pdf.exists() and not st.session_state.pdf_uploaded:
        if st.button("📚 Load Unit 2 Curriculum (2.1-2.7)"):
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
                    st.success("✅ Curriculum loaded!")
                    st.rerun()

    chip_query = None
    chip_topic = None

    st.markdown("#### Silk Road Learning Routes")
    
    active_concept = get_concept()
    if st.session_state.current_topic in ("General Tutoring", "", None):
        st.session_state.current_topic = active_concept["title"]
    st.caption(f"🧭 {active_concept['description']}")

    primer_col, challenge_col = st.columns([1, 1])
    with primer_col:
        if st.button("🎯 Route primer", use_container_width=True, help="Get an overview and learning roadmap for the Silk Road topic"):
            chip_query = active_concept["starter"]
            chip_topic = active_concept["title"]
    with challenge_col:
        if st.session_state.challenge_active:
            st.success("Challenge armed • +10 bonus XP on your next correct answer")
            if st.button("Cancel challenge", use_container_width=True, key="cancel_challenge_chat"):
                st.session_state.challenge_active = False
                save_persisted_state()
        else:
            if st.button("⚔️ Challenge Question", use_container_width=True, help="Receive a tough question for bonus XP"):
                st.session_state.challenge_active = True
                # Prompt tutor for challenge question
                challenge_prompt = (
                    "Present a challenging [QUIZ] question that tests deep understanding of "
                    f"{st.session_state.current_topic}. Make it thought-provoking and worthy of bonus XP. "
                    "The student has activated challenge mode."
                )
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
                save_persisted_state()
                st.toast("Challenge armed! Answer the tough question for +10 bonus XP.", icon="⚡")
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
        if st.button("✨ Surprise me", use_container_width=True):
            chip_query = f"Give me a fresh angle on {active_concept['title']} with a question to get started."
            chip_topic = active_concept["title"]

    ensure_initial_tutor_message(model)

    with st.container(border=True):
        for idx, m in enumerate(st.session_state.messages):
            with st.chat_message(m.role):
                if m.role == "user":
                    col1, col2 = st.columns([6, 1])
                    with col1:
                        if st.session_state.get("editing_message_idx") == idx:
                            edited_text = st.text_area(
                                "Edit message",
                                value=m.content,
                                key=f"edit_{idx}",
                                label_visibility="collapsed"
                            )
                            if st.button("Save", key=f"save_{idx}"):
                                st.session_state.messages[idx].content = edited_text
                                st.session_state.editing_message_idx = None
                                save_persisted_state()
                                st.rerun()
                        else:
                            st.markdown(m.content)
                    with col2:
                        if st.session_state.get("editing_message_idx") != idx:
                            if st.button("✏️", key=f"edit_btn_{idx}"):
                                st.session_state.editing_message_idx = idx
                                st.rerun()
                else:
                    st.markdown(m.content)

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
        with st.chat_message("user"):
            st.markdown(query)

        pending_type = st.session_state.question_type
        if st.session_state.awaiting_answer and pending_type:
            is_valid, xp, reason = check_answer_quality(
                query, pending_type, st.session_state.personality
            )
            if is_valid and xp > 0:
                award_xp(xp, reason or f"{pending_type.title()} response")
                metadata = {
                    "type": pending_type,
                    "xp_awarded": xp,
                    "reason": reason,
                    "personality": st.session_state.personality,
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
        
        with st.chat_message("assistant"):
            st.markdown(clean_reply)
        
        st.session_state.messages.append(
            Message(role="assistant", content=clean_reply, metadata={"question_type": question_type})
        )
        refresh_topic_periodically()
        save_persisted_state()
        
        if question_type:
            st.session_state.awaiting_answer = True
            st.session_state.question_type = question_type
        
        st.rerun()

    col_a, col_b = st.columns([1, 2])
    with col_a:
        if st.button("🔄 Reset chat", use_container_width=True):
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
                    xp_label = "15 XP for correct recall"
            else:
                xp_label = "25 XP for quiz mastery"
            st.info(f"⏳ Awaiting answer • {xp_label}")
        else:
            if st.session_state.challenge_active:
                st.caption("⚔️ Challenge armed: next correct answer earns +10 bonus XP on top of regular rewards.")
            else:
                st.caption("💡 Socratic Mini-Q: 10 XP • Narrative Mini-Q: 5-10 XP • Direct Mini-Q: 15 XP • Quiz: 25 XP")

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
                for k, v in state.items():
                    if k in ("xp", "level", "concept_progress", "subtopic_progress", "current_concept", "current_subtopic", "current_topic", "messages", "personality", "challenge_active"):
                        st.session_state[k] = v
                st.session_state.db_state_loaded = True
        except Exception:
            pass

    sidebar_nav()

    if st.session_state.page == "User Home":
        page_home()
    else:
        page_chat()

if __name__ == "__main__":
    main()