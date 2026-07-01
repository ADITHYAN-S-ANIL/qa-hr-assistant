# QA Chat - Advanced RAG AI Assistant

QA Chat is a premium Retrieval-Augmented Generation (RAG) chatbot platform designed for **QAWebPrints**. It allows users to have intelligent conversations with an AI that can be "trained" on custom documents and data.

## 🚀 Key Features

### 🧠 Intelligent Conversational AI
- **Dual Model Support**: Primarily uses **Gemini 2.0 Flash** for speed and accuracy.
- **Fail-Safe Reliability**: Implements automatic fallback to **Gemini 1.5 Flash** if rate limits (429 errors) are hit.
- **Smart Greetings**: Detects generic queries (like "Hi" or "Good morning") to respond with natural, conversational text instantly.

### 📚 Advanced RAG (Knowledge Base)
- **Document Training**: Upload PDF, TXT, MD, and other files to provide the AI with specific business context.
- **Hybrid Vector Storage**: 
  - Uses **PGVector** (PostgreSQL) for production-grade vector storage.
  - Automatically falls back to high-performance **FAISS** local indexing if the database extension is not available.
- **Manual Training**: Add website URLs or custom text directly through the UI to update the AI's "brain" in real-time.

### 🔐 Secure Authentication
- **GitHub OAuth**: Seamless login using your GitHub account.
- **Email/Password**: Standard secure registration and login.
- **Session Management**: Persistent chat history tied to your user account, stored in PostgreSQL.

### 🎨 Premium User Experience
- **Modern UI**: Sleek, dark-themed interface with glassmorphism effects and smooth transitions.
- **Responsive Design**: Optimized for both desktop and mobile viewing.
- **Chat Management**: Create multiple sessions, rename chats, and toggle RAG capabilities per conversation.

---

## 🛠️ Technology Stack

- **Frontend**: React, Vite, Framer Motion, Vanilla CSS (Premium Aethestics)
- **Backend**: Python, Flask, LangChain, Psycopg2
- **Database**: PostgreSQL (with PGVector), FAISS (Local Vector Store)
- **AI Models**: Google Gemini (via `langchain-google-genai`), Fallback support for Groq/OpenAI.

---

## ⚙️ Setup & Installation

### Backend Setup
1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your API keys:
   ```env
   GEMINI_API_KEY=your_key_here
   DB_HOST=localhost
   DB_NAME=qachat
   DB_USER=postgres
   DB_PASS=your_password
   SECRET_KEY=your_secret
   ```
5. Run the server:
   ```bash
   python app.py
   ```

### Frontend Setup
1. Navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

---

## 🔧 Recent Improvements (v1.1)

- **Fixed Windows Encoding**: Resolved `UnicodeEncodeError` by removing non-ASCII characters from system logs.
- **Rate Limit Resilience**: Added `safe_invoke` to prevent "An error occurred" messages during peak API usage.
- **Port Conflict Handling**: Optimized process management to prevent multiple instances from fighting over Port 5000.
- **Normal Text Responses**: Improved greeting detection for faster, more human-like interactions.

---

**Developed by Antigravity for QA Chat Project.**
