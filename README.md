# 🛒🎤 Smart Shopping List with Hebrew Voice AI

Real-time Hebrew voice commands → GPT-4 categorization → TTS responses. Built for smart fridges with WebRTC audio processing and intelligent product categorization.

![image](https://github.com/user-attachments/assets/9fc47730-83a3-4c31-b2f5-8377bd67abed)

## What's Actually Interesting

### 🎤 **End-to-End Hebrew Voice Pipeline**
- **OpenAI Whisper** for Hebrew STT with custom audio preprocessing
- **Edge TTS** (`he-IL-HilaNeural`) for natural Hebrew responses  
- **WebRTC MediaRecorder** → **FastAPI** → **AI Agent** → **Audio Response** in <2s
- Voice-optimized agent responses (no markdown, max 10 words, emoji-free)

### 🧠 **GPT-4 Shopping Intelligence**
- Context-aware Hebrew product categorization (`מיונז` → `תבלינים ורטבים`)
- Israeli brand recognition (`תנובה`, `שטראוס`, etc.)
- Smart fallback processing when agent unavailable
- Real-time list synchronization with category statistics



### 🏠 **Smart Appliance Optimized**
- **RTL Hebrew interface** designed for 10"+ touchscreens
- **Floating category navigation** for one-handed operation
- **Real-time polling** (2s intervals) for multi-user sync
- **Responsive voice feedback** with visual confirmation
- Windows file locking fixes for embedded systems

![Untitled video](https://github.com/user-attachments/assets/947786c2-4dc6-4702-8629-7c1b6319f611)


## Tech Stack That Matters

```python
# Voice Processing Pipeline
MediaRecorder → FastAPI → Whisper API → GPT-4 Agent → Edge TTS → Audio Response

# Smart Agent Architecture  
Agno Framework + GPT-4 + Custom Hebrew Instructions + Shopping Toolkit

# Frontend
Vanilla JS + WebRTC + Real-time polling + RTL CSS Grid
```

## Core Voice Commands
```hebrew
"תוסיף חלב לרשימה"     → Adds milk to dairy category
"מה יש בירקות?"        → Lists vegetable items  
"תסמן חלב כהושלם"      → Marks item completed
```

## Quick Setup
```bash
git clone <repo>
pip install openai edge-tts fastapi agno python-multipart
echo "OPENAI_API_KEY=sk-..." > .env
python server.py
# → http://localhost:8000
```

## API Highlights

**Voice Command Processing:**
```python
POST /api/voice-command
# WebM audio → Hebrew transcription → AI response → MP3 TTS
```

**Smart Categorization:**
```python
POST /api/add-item
{"name": "מיונז", "quantity": "1"} 
# → Auto-categorized to "תבלינים ורטבים"
```

## Architecture Notes

- **Agent Response Cleaning:** Strips markdown/emojis before TTS
- **Temp File Handling:** Windows-compatible file locking with cleanup
- **Category Intelligence:** 12 Hebrew categories with fallback logic  
- **Real-time Sync:** WebSocket-style polling for multi-device updates
- **Voice UI Patterns:** Recording states, error handling, audio playback management

Built for Samsung Smart Fridge integration but works anywhere with a microphone.

## License
MIT
