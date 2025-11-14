# TutorQuest - Gamified AI Tutoring Platform

An intelligent, gamified tutoring platform powered by Google Gemini AI with multiple teaching personalities and XP-based progression.

## Features

### 🎓 Three Tutor Personalities

1. **Socratic (📚 "The Questioner")**
   - Guides by asking layered, open-ended questions
   - Pushes you to cite evidence and reason step-by-step
   - Rewards thoughtful reasoning with +10 XP

2. **Narrative (📖 "The Storyteller")**
   - Immerses you in short historical scenes and role-play
   - Encourages empathy, predictions, and creative thinking
   - Rewards accurate insight with +10 XP and creative engagement with +5 XP

3. **Direct (🎯 "The Instructor")**
   - Delivers curriculum-aligned lessons in clear chunks
   - Checks comprehension after each section with quick recall questions
   - Rewards correct answers with +15 XP and runs end-of-topic quizzes

### 📝 Quiz System

- **Mini-Questions** ([MINI-Q]): Learning checkpoints worth 10 XP
- **Quizzes** ([QUIZ]): Mastery assessments worth 25 XP
- Automatic XP rewards for quality answers
- Progress tracking for questions answered

### 📄 PDF Curriculum Support

- Upload PDFs for the tutor to reference
- Built-in support for local curriculum files
- Tutor adapts teaching to match curriculum content

### 🎮 Gamification

- XP system with level progression (100 XP per level)
- Progress bars and stat tracking
- Daily action bonuses
- Badge system for achievements
- Celebration animations on level-up

## Setup

### Quick Start (macOS/zsh)

```bash
# 1. Clone or navigate to project
cd Gamified_app

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up API key (choose one):

# Option A: .env file (recommended for local dev)
echo 'GEMINI_API_KEY=your_key_here' > .env

# Option B: Environment variable
export GEMINI_API_KEY="your_key_here"

# 5. Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501` (or 8502 if 8501 is busy).

## Usage

### User Home Page
- View your level, XP, and progress
- Track questions answered, mini-Qs, and quizzes
- Complete daily actions for bonus XP
- View earned badges

### Tutoring Chat Page
1. **Select Personality**: Choose your preferred tutor style from the sidebar
2. **Load Curriculum** (optional): Upload a PDF or load the built-in Unit 2 curriculum
3. **Start Learning**: Use quick-start buttons or type your own questions
4. **Answer Questions**: Respond to [MINI-Q] and [QUIZ] prompts to earn XP
5. **Track Progress**: Watch your XP and level grow as you learn!

### Earning XP
- Socratic [MINI-Q]: +10 XP for evidence-based reasoning
- Narrative [MINI-Q]: +5 XP for creative engagement, +10 XP for historically accurate insight
- Direct [MINI-Q]: +15 XP for correct recall
- Any [QUIZ] question answered correctly: +25 XP
- Practice button: +15 XP
- Lesson button: +30 XP
- Streak button: +10 XP

## Configuration

### Theme
Light blue theme configured in `.streamlit/config.toml`:
- Primary Color: #5DADE2 (soft blue)
- Background: #F8FBFF (light blue-white)

### Streamlit Secrets (for deployment)
Add to `.streamlit/secrets.toml` or Streamlit Cloud secrets:
```toml
GEMINI_API_KEY = "your_key_here"
```

## Project Structure

```
Gamified_app/
├── app.py                 # Main application
├── .env                   # API keys (gitignored)
├── .streamlit/
│   └── config.toml       # Theme configuration
├── requirements.txt       # Python dependencies
├── Unit 2_ 2.1-2.7.pdf   # Sample curriculum
└── README.md             # This file
```

## API Key
This project uses Google Gemini AI. Get your free API key at:
https://makersuite.google.com/app/apikey

## Dependencies
- `streamlit>=1.37` - Web framework
- `google-generativeai>=0.8.0` - Gemini AI SDK
- `python-dotenv>=1.0` - Environment variable management

## Tips
- Try different personalities to find your learning style
- Answer mini-questions to build understanding gradually
- Upload relevant PDFs for personalized curriculum-based learning
- Maintain daily streaks for consistent XP growth
# gamifiedapp
