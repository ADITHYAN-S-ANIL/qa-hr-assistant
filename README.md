# QA HR Assistant
### AI-Powered HR Management System for QAWebPrints Infocorp LLP

> A full-stack HR Intelligence platform with a local AI assistant powered by **Ollama** (no external API keys required). The AI assistant answers any question about employees, tasks, and leave requests using **live database data**.

---

## 📋 Table of Contents
- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Setup Guide (New System)](#setup-guide-new-system)
  - [1. Install Ollama](#1-install-ollama)
  - [2. Install PostgreSQL](#2-install-postgresql)
  - [3. Clone the Repository](#3-clone-the-repository)
  - [4. Setup the Backend](#4-setup-the-backend)
  - [5. Setup the Frontend](#5-setup-the-frontend)
  - [6. Run the Project](#6-run-the-project)
- [Environment Variables](#environment-variables)
- [How the AI Assistant Works](#how-the-ai-assistant-works)
- [Project Structure](#project-structure)
- [Roles & Permissions](#roles--permissions)

---

## 🧾 Project Overview

The **QA HR Assistant** is an internal HR management web application that provides:
- **Role-based dashboards** for CEO, Manager, HR, and Employee.
- **Task tracking** — log, assign, and monitor the status of work items.
- **Leave management** — apply, approve, and reject leave requests.
- **AI-powered chatbot** — an HR Intelligence assistant that answers natural language questions like *"How many employees do we have?"* or *"Who applied for leave this week?"* using **live, real-time data from the database**.

The entire AI system runs **100% locally using Ollama** — no OpenAI, no Anthropic, no external API keys.

---

## 🛠 Tech Stack

| Layer      | Technology                            |
|------------|---------------------------------------|
| Frontend   | React.js, Vite, Vanilla CSS           |
| Backend    | Python 3.x, Flask                     |
| Database   | PostgreSQL                            |
| AI Engine  | Ollama (local LLM inference)          |
| AI Framework | LangChain (prompt assembly)         |
| Auth       | JWT (JSON Web Tokens)                 |

---

## ✅ Prerequisites

Before starting, make sure you have the following installed:
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/en/download)
- [PostgreSQL 14+](https://www.postgresql.org/download/)
- [Git](https://git-scm.com/downloads)
- [Ollama](https://ollama.com/download)

---

## 🚀 Setup Guide (New System)

Follow these steps **in order** when setting up on any new machine.

### 1. Install Ollama

**Windows:**
1. Download the installer from [https://ollama.com/download](https://ollama.com/download)
2. Run the installer and follow the setup wizard.
3. After install, open a new terminal and verify it works:
   ```bash
   ollama --version
   ```

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Pull the required AI model:**
After Ollama is installed, download the model used by this project:
```bash
ollama pull llama3.2
```
> This downloads the Llama 3.2 model (~2GB). This is a one-time download.
> After pulling, Ollama runs as a background service automatically on port `11434`.

To verify the model is ready:
```bash
ollama list
```
You should see `llama3.2` in the list.

---

### 2. Install PostgreSQL

1. Download from [https://www.postgresql.org/download/](https://www.postgresql.org/download/)
2. During setup, remember the **password** you set for the `postgres` user.
3. After installation, open **pgAdmin** or the **psql** shell and create the database:
   ```sql
   CREATE DATABASE qa_hr_db;
   ```

---

### 3. Clone the Repository

```bash
git clone https://github.com/ADITHYAN-S-ANIL/qa-hr-assistant.git
cd qa-hr-assistant
```

---

### 4. Setup the Backend

**a) Create a Python virtual environment:**
```bash
cd backend
python -m venv .venv
```

**b) Activate the virtual environment:**

On **Windows:**
```bash
.venv\Scripts\activate
```
On **macOS / Linux:**
```bash
source .venv/bin/activate
```

**c) Install required Python packages:**
```bash
pip install -r requirements.txt
```

**d) Create your `.env` file:**

Copy the example file and fill in your details:
```bash
copy .env.example .env        # Windows
cp .env.example .env          # macOS/Linux
```

Now open `.env` and set the values (see [Environment Variables](#environment-variables) section below).

**e) Initialize the database tables:**
```bash
python init_db.py
```

---

### 5. Setup the Frontend

```bash
cd ../frontend
npm install
```

---

### 6. Run the Project

You need to run **3 services** simultaneously. Open **3 separate terminal windows**.

**Terminal 1 — Start Ollama (if not already running):**
```bash
ollama serve
```

**Terminal 2 — Start the Backend (Flask API):**
```bash
cd backend
.venv\Scripts\activate      # Windows
# OR
source .venv/bin/activate    # macOS/Linux

python app.py
```
> The backend will start on `http://localhost:5000`

**Terminal 3 — Start the Frontend (React + Vite):**
```bash
cd frontend
npm run dev
```
> The frontend will start on `http://localhost:5173`

**Now open your browser and navigate to:** `http://localhost:5173`

---

## 🔐 Environment Variables

Create a file named `.env` inside the `backend/` folder with the following content:

```env
# PostgreSQL Database Connection
DB_HOST=localhost
DB_PORT=5432
DB_NAME=qa_hr_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password_here

# JWT Secret Key (use any long random string)
JWT_SECRET_KEY=your_super_secret_key_change_this_in_production

# Ollama Configuration (default, no changes needed)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

> **Important:** Never commit the `.env` file. It is already listed in `.gitignore`.

---

## 🤖 How the AI Assistant Works

The HR Intelligence Assistant uses a **"Live Data Snapshot Injection"** pattern:

1. **User asks a question** — e.g., *"Who applied for leave?"*
2. **Backend fetches live data** — Executes 3 SQL queries to get the current state of Employees, Tasks, and Leave Requests from PostgreSQL.
3. **Data is injected** — The raw SQL data is formatted as text and injected directly into the Ollama model's system prompt.
4. **Ollama answers** — The local LLM reads the injected real data and answers the question accurately in natural language.

**No keywords needed. No external APIs. 100% private and local.**

```
CEO: "How many employees are on leave?"
         ↓
Backend → PostgreSQL → Live Leave Data
         ↓
Data injected into Ollama system prompt
         ↓
Ollama: "Currently 1 employee is on approved leave: Arjun (regular leave on 2026-06-26)."
```

---

## 📁 Project Structure

```
qa-hr-assistant/
├── backend/
│   ├── app.py              # Main Flask app & all API routes
│   ├── init_db.py          # Database schema initializer
│   ├── mock_leave_api.py   # Mock leave management microservice
│   ├── requirements.txt    # Python dependencies
│   ├── .env.example        # Environment variable template
│   └── .env                # Your local config (DO NOT COMMIT)
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Dashboards/
│   │   │   │   ├── CEODashboard.jsx
│   │   │   │   ├── ManagerDashboard.jsx
│   │   │   │   ├── EmployeeDashboard.jsx
│   │   │   │   └── FloatingChatbot.jsx
│   │   │   ├── Login.jsx
│   │   │   └── Layout/
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

---

## 👥 Roles & Permissions

| Role     | Can See                                   | AI Assistant Access |
|----------|-------------------------------------------|---------------------|
| CEO      | All employees, all tasks, all leaves      | Full company data   |
| Manager  | Their team's tasks and leaves             | Team-scoped data    |
| HR       | All employees and leave requests          | HR-scoped data      |
| Employee | Their own tasks and leaves only           | Personal data only  |

---

## 💡 Troubleshooting

**Ollama not responding?**
```bash
# Check if Ollama is running
ollama list
# If not, start it:
ollama serve
```

**Backend can't connect to DB?**
- Double check your `.env` file has the correct `DB_PASSWORD`.
- Make sure the `qa_hr_db` database was created in PostgreSQL.

**Frontend shows blank page?**
- Make sure the backend is running on port `5000`.
- Check the browser console for errors.

---

## 📄 License
Internal project — QAWebPrints Infocorp LLP. All rights reserved.
