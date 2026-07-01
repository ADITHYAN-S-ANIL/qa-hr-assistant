# QA HR Assistant
### AI-Powered HR Management System for QAWebPrints Infocorp LLP

> A full-stack HR Intelligence platform with a local AI chatbot powered entirely by **Ollama** (no external API keys required). The AI assistant answers any natural language question about employees, tasks, and leave requests using **live PostgreSQL database data**.

---

## 📋 Table of Contents
- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Part 1 — Ollama Setup (Detailed)](#part-1--ollama-setup-detailed)
- [Part 2 — Database Setup & Connection](#part-2--database-setup--connection)
- [Part 3 — How the HR Assistant Connects to the Database](#part-3--how-the-hr-assistant-connects-to-the-database)
- [Part 4 — Backend Setup](#part-4--backend-setup)
- [Part 5 — Frontend Setup](#part-5--frontend-setup)
- [Part 6 — Running on a Server (Production/Another Machine)](#part-6--running-on-a-server-productionanother-machine)
- [Environment Variables](#environment-variables)
- [Roles & Permissions](#roles--permissions)
- [Troubleshooting](#troubleshooting)

---

## 🧾 Project Overview

The **QA HR Assistant** is an internal HR management system that includes:
- **Role-based dashboards** for CEO, Manager, HR, and Employee
- **Task tracking** — log, assign, and monitor work items
- **Leave management** — apply, approve, and reject leave requests
- **AI-powered HR Chatbot** — answers natural language questions like *"Who applied for leave?"* or *"Show all pending tasks"* using **100% live, real-time data from PostgreSQL**

The entire AI system runs **locally using Ollama** — no OpenAI, no Anthropic, no external API keys, no internet required after setup.

---

## 🛠 Tech Stack

| Layer        | Technology                         |
|--------------|------------------------------------|
| Frontend     | React.js, Vite, Vanilla CSS        |
| Backend      | Python 3.x, Flask                  |
| Database     | PostgreSQL                         |
| DB Driver    | psycopg2 (Python ↔ PostgreSQL)     |
| AI Engine    | Ollama (local LLM inference)       |
| AI Framework | LangChain (prompt & message assembly) |
| Auth         | JWT (JSON Web Tokens)              |

---

## ✅ Prerequisites

Make sure the following are installed before starting:
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- [PostgreSQL 14+](https://www.postgresql.org/download/)
- [Git](https://git-scm.com/)
- [Ollama](https://ollama.com/download)

---

## Part 1 — Ollama Setup (Detailed)

Ollama is the engine that runs the AI model locally on your machine. It works like a local server — once running, Flask connects to it to generate AI responses.

### 1.1 Install Ollama

**Windows:**
1. Go to [https://ollama.com/download](https://ollama.com/download)
2. Download the Windows installer and run it
3. After install, open a terminal and verify:
   ```bash
   ollama --version
   ```

**macOS:**
```bash
brew install ollama
```

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

---

### 1.2 Start the Ollama Service

Ollama must be running before the backend starts. It listens on `http://localhost:11434` by default.

```bash
ollama serve
```

To run it in the background (Linux/macOS):
```bash
nohup ollama serve &
```

To verify it is running:
```bash
curl http://localhost:11434
# Should return: "Ollama is running"
```

---

### 1.3 Pull the AI Model

This project uses **Llama 3.2** by default. Pull it once (requires internet, ~2GB download):

```bash
ollama pull llama3.2
```

Verify the model is ready:
```bash
ollama list
# Should show: llama3.2   ...   (size)
```

You can test the model manually to confirm it is working:
```bash
ollama run llama3.2 "How many employees does QAWebPrints have?"
```

---

### 1.4 How Flask Connects to Ollama

In `backend/app.py`, the LangChain library is used to connect Flask to the local Ollama server:

```python
from langchain_ollama import ChatOllama

def get_llm(model_choice='llama'):
    return ChatOllama(
        model="llama3.2",
        base_url="http://localhost:11434",  # Ollama server address
        temperature=0.3                     # Lower = more factual, less creative
    )
```

Every time a user sends a chat message, Flask:
1. Fetches live data from PostgreSQL
2. Builds a prompt with that data
3. Sends the prompt to Ollama via LangChain
4. Returns Ollama's response to the frontend

---

## Part 2 — Database Setup & Connection

### 2.1 Install PostgreSQL

Download from [https://www.postgresql.org/download/](https://www.postgresql.org/download/)

During setup:
- Remember the **username** (default: `postgres`) and **password** you set
- Keep the default port: **5432**

### 2.2 Create the Database

Open pgAdmin or the psql terminal:

```sql
CREATE DATABASE qa_hr_db;
```

### 2.3 Initialize Tables

After cloning the project and setting up `.env`, run:

```bash
cd backend
python init_db.py
```

This creates all required tables:
- `users` — employee accounts and roles
- `tasks` — work assignments
- `leaves` — leave requests
- `sessions` — chat history storage

### 2.4 How Flask Connects to PostgreSQL

In `backend/app.py`, a connection is established using `psycopg2`:

```python
import psycopg2

def get_db():
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "qa_hr_db"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "")
    )
    return conn
```

All values are read from the `.env` file — never hardcoded.

---

## Part 3 — How the HR Assistant Connects to the Database

This is the most important part. Here is the **exact flow** of how the AI chatbot reads from the database and answers questions:

### Step-by-Step Flow

```
User types: "Who applied for leave?"
         |
         ▼
Flask /api/chat endpoint receives the message
         |
         ▼
_fetch_live_company_data(user_id, role) is called
  → SQL Query 1: SELECT all employees from `users` table
  → SQL Query 2: SELECT all tasks from `tasks` table
  → SQL Query 3: SELECT all leave requests from `leaves` table
         |
         ▼
All SQL results are formatted into a readable text block:
  "=== EMPLOYEES ===
   - arjun@qawebprints.com (Role: employee)
   - govindh@1234gmail.com (Role: manager)
   ...
   === LEAVE REQUESTS ===
   - [APPROVED] arjun@qawebprints.com applied for regular leave on 2026-06-26"
         |
         ▼
This text is injected into Ollama's System Prompt via LangChain:
  SystemMessage: "You are the HR Assistant. Use ONLY the data below to answer..."
  HumanMessage: "Who applied for leave?"
         |
         ▼
Ollama reads the injected data and replies:
  "Arjun applied for regular leave on 2026-06-26. It has been approved."
         |
         ▼
Flask returns the response to the React frontend
```

### The Database Query Code

```python
def _fetch_live_company_data(user_id, user_role):
    conn = get_db()
    with conn.cursor() as cur:

        # Fetch employees (CEO sees all, Manager sees team only)
        if user_role == 'ceo':
            cur.execute("SELECT email, role, employee_id FROM users")
        elif user_role == 'manager':
            cur.execute("SELECT email, role FROM users WHERE manager_id = %s", (user_id,))

        # Fetch tasks
        cur.execute("""
            SELECT u.email, t.description, t.status, t.date
            FROM tasks t JOIN users u ON t.user_id = u.id
        """)

        # Fetch leave requests (uses 'type' column, not 'leave_type')
        cur.execute("""
            SELECT u.email, l.type, l.start_date, l.end_date, l.reason, l.status
            FROM leaves l JOIN users u ON l.user_id = u.id
        """)
```

### Why This Approach (No Keywords Needed)

Old approach (broken): The AI guessed which database function to call → hallucinations, routing errors.

New approach (current): The backend fetches ALL data upfront and gives it directly to Ollama → the AI simply reads the data and answers. No guessing. No tools. No keywords required.

---

## Part 4 — Backend Setup

```bash
# 1. Navigate to backend folder
cd backend

# 2. Create Python virtual environment
python -m venv .venv

# 3. Activate it
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # macOS/Linux

# 4. Install all dependencies
pip install -r requirements.txt

# 5. Create your .env file
copy .env.example .env       # Windows
cp .env.example .env         # macOS/Linux
# Open .env and fill in your database password and JWT secret

# 6. Initialize the database
python init_db.py

# 7. Start the backend server
python app.py
# Flask API will run on: http://localhost:5000
```

---

## Part 5 — Frontend Setup

```bash
cd frontend
npm install
npm run dev
# React app will run on: http://localhost:5173
```

---

## Part 6 — Running on a Server (Production/Another Machine)

When deploying this project on a **different computer or a Linux server**, follow these steps:

### 6.1 On the Server — Install All Prerequisites

```bash
# Install Python
sudo apt install python3 python3-pip python3-venv -y

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

### 6.2 Pull the AI Model on the New Server

```bash
ollama pull llama3.2
```

### 6.3 Clone & Configure

```bash
git clone https://github.com/ADITHYAN-S-ANIL/qa-hr-assistant.git
cd qa-hr-assistant

# Setup backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # Fill in your DB_HOST, DB_PASSWORD, JWT_SECRET_KEY
python3 init_db.py

# Setup frontend
cd ../frontend
npm install
```

### 6.4 Run All Services on a Server

Use **3 separate terminal sessions** (or use `screen`/`tmux`):

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Backend
cd backend && source .venv/bin/activate && python3 app.py

# Terminal 3: Start Frontend
cd frontend && npm run dev
```

### 6.5 Run as Background Services (Production)

For long-running server deployment, use `systemd` or `pm2`:

**Backend with systemd:**
```bash
sudo nano /etc/systemd/system/qa-backend.service
```
```ini
[Unit]
Description=QA HR Assistant Backend
After=network.target

[Service]
WorkingDirectory=/path/to/qa-hr-assistant/backend
ExecStart=/path/to/.venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable qa-backend
sudo systemctl start qa-backend
```

**Ollama as a service (auto-start):**
Ollama automatically registers itself as a systemd service on Linux during installation.
```bash
sudo systemctl enable ollama
sudo systemctl start ollama
```

**Frontend with PM2:**
```bash
npm install -g pm2
cd frontend
pm2 start "npm run dev" --name qa-frontend
pm2 startup
pm2 save
```

---

## 🔐 Environment Variables

Create `backend/.env` from the template:

```env
# PostgreSQL Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=qa_hr_db
DB_USER=postgres
DB_PASSWORD=your_password_here

# JWT Secret (use a long random string)
JWT_SECRET_KEY=change_this_to_a_long_random_string

# Ollama Configuration (no changes needed for local setup)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

> ⚠️ **Never commit `.env` to GitHub.** It is listed in `.gitignore`.

---

## 👥 Roles & Permissions

| Role     | Dashboard Data Visible              | AI Chatbot Access       |
|----------|-------------------------------------|-------------------------|
| CEO      | All employees, all tasks, all leaves | Full company data       |
| Manager  | Their team's tasks and leaves        | Team-scoped data only   |
| HR       | All employees and leave requests     | HR-scoped data          |
| Employee | Own tasks and own leaves only        | Personal data only      |

---

## 💡 Troubleshooting

**Ollama not responding?**
```bash
# Check status
curl http://localhost:11434
# Restart it
ollama serve
```

**Model not found?**
```bash
ollama list          # Check what models are available
ollama pull llama3.2 # Re-download if missing
```

**Backend can't connect to database?**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql     # Linux
# Check your .env DB_PASSWORD matches your PostgreSQL password
```

**Frontend shows blank page or proxy error?**
- Make sure the backend Flask server is running on port `5000`
- Check `frontend/vite.config.js` proxy setting points to `http://localhost:5000`

**AI gives wrong answers?**
- The Ollama model needs to be running (`ollama serve`)
- Ensure the correct model is pulled (`ollama list` should show `llama3.2`)

---

## 📄 License
Internal project — QAWebPrints Infocorp LLP. All rights reserved.
