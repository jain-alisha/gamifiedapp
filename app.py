import os
import json
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

NEXT_LEVEL_XP = 100
STATE_FILE = Path(__file__).with_name("state_store.json")


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
    data = {
        "xp": st.session_state.get("xp", 0),
        "level": st.session_state.get("level", 1),
    }
    try:
        with STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        st.warning("Unable to persist XP locally.")

@dataclass
class Message:
    role: str
    content: str
    metadata: Optional[Dict] = None

def init_state():
    persisted = load_persisted_state()
    persisted_xp = persisted.get("xp", 0)
    computed_level = 1 + persisted_xp // NEXT_LEVEL_XP
    defaults = {
        "page": "User Home",
        "xp": persisted_xp,
        "level": max(persisted.get("level", 1), computed_level),
        "messages": [],
        "personality": "Socratic",
        "awaiting_answer": False,
        "question_type": None,
        "pdf_uploaded": False,
    "pdf_file_ref": None,
        "current_topic": "General Tutoring",
    "chat_session": None,
    "chat_session_personality": None,
        "chat_session_pdf_id": None,
        "intro_sent": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

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

If the learner says they do not know, offer a short explanation or hint, then follow up with a simpler question.

Tone: respectful, curious, mentor-like. Guide discovery step-by-step.

Tagging rules:
- Use [MINI-Q] before learning checkpoint questions worth 10 XP.
- Use [QUIZ] before mastery questions that validate understanding (25 XP).
''',

    "Narrative": '''You are a narrative-style history tutor who teaches through immersive storytelling and historical role-play.

Always:
- Frame each topic as a short scene or chapter with time, place, and emotion.
- Give the student a role inside the story and ask what they see, feel, or predict.
- Reward thoughtful or empathetic responses with XP (+10 XP for accurate historical insight, +5 XP for creative engagement).
- Reveal what actually happened and explain its significance after the student responds.
- Keep story segments to three to five interactions, then recap key facts.

Tone: cinematic, engaging, vivid. Avoid dry fact lists.

Tagging rules:
- Use [MINI-Q] for in-story checkpoints (award 5–10 XP depending on depth of response).
- Use [QUIZ] for short end-of-story quizzes (25 XP for correct answers).
''',

    "Direct": '''You are a direct, structured history tutor who delivers curriculum-aligned lessons clearly and efficiently.

Always:
- Start with an overview of the lesson objective.
- Present concise factual content in short chunks.
- After each chunk, ask a quick comprehension check tagged with [MINI-Q] and award +15 XP for correct answers.
- Provide immediate, friendly feedback and short corrections, including optional hints.
- End each topic with a three to five question [QUIZ] that reinforces key facts, award 25 XP for correct answers, and highlight module completion.

Tone: friendly, clear, supportive — like a teacher reviewing notes alongside the student.
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

def sidebar_nav():
    with st.sidebar:
        st.markdown("## 🎓 TutorQuest")
        st.caption("Gamified tutoring, powered by AI")
        
        page = st.radio(
            "Navigate",
            ["User Home", "Tutoring Chat"],
            index=0 if st.session_state.page == "User Home" else 1,
        )
        st.session_state.page = page
        st.divider()
        
        if st.session_state.page == "Tutoring Chat":
            st.markdown("### Tutor Personality")
            personalities = ["Socratic", "Narrative", "Direct"]
            if st.session_state.personality not in personalities:
                st.session_state.personality = "Socratic"
            personality = st.selectbox(
                "Select teaching style:",
                personalities,
                index=personalities.index(st.session_state.personality),
                help="Choose how your tutor teaches"
            )
            if personality != st.session_state.personality:
                st.session_state.personality = personality
                st.session_state.chat_session = None
                st.session_state.chat_session_personality = None
                st.session_state.chat_session_pdf_id = None
                st.session_state.messages = []
                st.session_state.awaiting_answer = False
                st.session_state.question_type = None
                st.session_state.current_topic = "General Tutoring"
                st.session_state.intro_sent = False
                st.rerun()
            
            descriptions = {
                "Socratic": "📚 Guides you with layered questions",
                "Narrative": "📖 Immerses you in historical stories",
                "Direct": "🎯 Delivers clear, structured lessons"
            }
            st.caption(descriptions[personality])
            st.divider()
        
        st.metric("Level", st.session_state.level)
        st.metric("XP", st.session_state.xp)
        st.progress(level_progress(st.session_state.xp))

def page_home():
    st.title("Welcome back 👋")
    st.caption("Track your learning streaks, XP, and level progress.")

    col1, col2, col3 = st.columns([2.2, 3.2, 1.6])

    with col1:
        st.markdown("#### Profile")
        st.image(
            "https://avatars.githubusercontent.com/u/9919?s=200&v=4",
            caption="Your Avatar",
            use_container_width=True,
        )
        st.metric("Level", st.session_state.level)
        st.metric("XP", st.session_state.xp)

    with col2:
        st.markdown("#### Progress to next level")
        current = st.session_state.xp % NEXT_LEVEL_XP
        remaining = NEXT_LEVEL_XP - current
        st.write(f"XP to next level: {remaining}")
        st.progress(
            level_progress(st.session_state.xp),
            text=f"{current}/{NEXT_LEVEL_XP}",
        )
        st.markdown("\n")
        c21, c22, c23 = st.columns(3)
        with c21:
            st.metric("Questions", len([m for m in st.session_state.messages if m.role == "user"]))
        with c22:
            mini_qs = len([m for m in st.session_state.messages if hasattr(m, 'metadata') and m.metadata and m.metadata.get("type") == "mini"])
            st.metric("Mini-Qs", mini_qs)
        with c23:
            quizzes = len([m for m in st.session_state.messages if hasattr(m, 'metadata') and m.metadata and m.metadata.get("type") == "quiz"])
            st.metric("Quizzes", quizzes)

    with col3:
        st.markdown("#### Badges")
        st.write("🏅 Starter")
        if st.session_state.level >= 2:
            st.write("🎯 Focused Learner")
        if st.session_state.level >= 5:
            st.write("🔥 Knowledge Seeker")

    st.markdown("---")
    st.subheader("Daily actions")
    a1, a2, a3, a4 = st.columns([1.2, 1.2, 1.2, 2])
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
        st.caption("Complete actions daily.")

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
                    st.success("✅ Curriculum loaded!")
                    st.rerun()

    st.markdown("##### Quick starts:")
    pp1, pp2, pp3, _ = st.columns([1.4, 1.6, 1.8, 2])
    chip_query = None
    chip_topic = None
    
    quick_starts = {
        "Socratic": [
            ("Causes of the French Revolution", "Guide me through why French citizens questioned the monarchy in 1789."),
            ("Industrial Revolution impacts", "Help me reason through how the Industrial Revolution changed workers' lives."),
            ("Civil Rights strategies", "Ask me guiding questions about tactics used during the Civil Rights Movement.")
        ],
        "Narrative": [
            ("Renaissance marketplace", "Put me in a Florentine marketplace in 1500 and narrate what I experience."),
            ("Trenches of WWI", "Tell the story of a soldier in 1917 and ask how I would react."),
            ("Harlem Renaissance club", "Let me experience a night in a Harlem jazz club and predict what happens next.")
        ],
        "Direct": [
            ("World War I causes", "Teach me the main causes of World War I step by step."),
            ("Reconstruction summary", "Walk me through the key points of Reconstruction after the US Civil War."),
            ("Cold War overview", "Give me a clear outline of the early Cold War and quiz me afterward.")
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

    ensure_initial_tutor_message(model)

    with st.container(border=True):
        for m in st.session_state.messages:
            with st.chat_message(m.role):
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
        with st.chat_message("user"):
            st.markdown(query)

        if st.session_state.awaiting_answer and st.session_state.question_type:
            is_valid, xp, reason = check_answer_quality(
                query, st.session_state.question_type, st.session_state.personality
            )
            if is_valid and xp > 0:
                award_xp(xp, reason or f"{st.session_state.question_type.title()} response")
                st.session_state.messages[-1].metadata = {
                    "type": st.session_state.question_type,
                    "xp_awarded": xp,
                    "reason": reason,
                    "personality": st.session_state.personality,
                }
            st.session_state.awaiting_answer = False
            st.session_state.question_type = None
        elif topic_update:
            words = topic_update.split()
            trimmed = " ".join(words[:8])
            if len(words) > 8:
                trimmed += "..."
            st.session_state.current_topic = trimmed

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
            st.session_state.current_topic = "General Tutoring"
            st.session_state.chat_session = None
            st.session_state.chat_session_personality = None
            st.session_state.chat_session_pdf_id = None
            st.session_state.intro_sent = False
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

def main():
    st.set_page_config(
        page_title="TutorQuest",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    init_state()
    apply_styles()
    sidebar_nav()

    if st.session_state.page == "User Home":
        page_home()
    else:
        page_chat()

if __name__ == "__main__":
    main()
