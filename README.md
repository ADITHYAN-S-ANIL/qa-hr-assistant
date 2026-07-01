# QA HR Assistant
### AI-Powered HR Management System for QAWebPrints Infocorp LLP

A full-stack HR Intelligence platform with a local AI chatbot powered entirely by **Ollama** (no external API keys required). The AI assistant answers any natural language question about employees, tasks, and leave requests using **live PostgreSQL database data**.

---

## Table of Contents
- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Part 1 - Ollama Setup (Detailed)](#part-1---ollama-setup-detailed)
- [Part 2 - Database Setup and Connection](#part-2---database-setup-and-connection)
- [Part 3 - How the HR Assistant Connects to the Database](#part-3---how-the-hr-assistant-connects-to-the-database)
- [Part 4 - Backend Setup](#part-4---backend-setup)
- [Part 5 - Frontend Setup](#part-5---frontend-setup)
- [Part 6 - Running on a Server](#part-6---running-on-a-server)
- [Part 7 - Integrating into an Existing Node.js Portal](#part-7---integrating-into-an-existing-nodejs-portal)
- [Environment Variables](#environment-variables)
- [Roles and Permissions](#roles-and-permissions)
- [Troubleshooting](#troubleshooting)

---

## Project Overview

The **QA HR Assistant** is an internal HR management system that includes:
- **Role-based dashboards** for CEO, Manager, HR, and Employee
- **Task tracking** - log, assign, and monitor work items
- **Leave management** - apply, approve, and reject leave requests
- **AI-powered HR Chatbot** - answers natural language questions like *"Who applied for leave?"* using **live, real-time data from PostgreSQL**

The entire AI system runs **locally using Ollama** - no OpenAI, no Anthropic, no external API keys.

---

## Tech Stack

| Layer        | Technology                         |
|--------------|------------------------------------|
| Frontend     | React.js, Vite, Vanilla CSS        |
| Backend      | Python 3.x, Flask                  |
| Database     | PostgreSQL                         |
| DB Driver    | psycopg2 (Python to PostgreSQL)    |
| AI Engine    | Ollama (local LLM inference)       |
| AI Framework | LangChain (prompt assembly)        |
| Auth         | JWT (JSON Web Tokens)              |

---

## Prerequisites

Make sure the following are installed:
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- [PostgreSQL 14+](https://www.postgresql.org/download/)
- [Git](https://git-scm.com/)
- [Ollama](https://ollama.com/download)

---

## Part 1 - Ollama Setup (Detailed)

Ollama is the engine that runs the AI model locally on your machine. It works like a local server - once running, Flask connects to it to generate AI responses.

### 1.1 Install Ollama

**Windows:**
1. Go to https://ollama.com/download
2. Download the Windows installer and run it
3. After install, open a terminal and verify:
   ```
   ollama --version
   ```

**macOS:**
```
brew install ollama
```

**Linux (Ubuntu/Debian):**
```
curl -fsSL https://ollama.com/install.sh | sh
```

### 1.2 Start the Ollama Service

Ollama must be running before the backend starts. It listens on `http://localhost:11434`.

```
ollama serve
```

To run it in the background on Linux/macOS:
```
nohup ollama serve &
```

To verify it is running:
```
curl http://localhost:11434
# Should return: Ollama is running
```

### 1.3 Pull the AI Model

This project uses Llama 3.2 by default. Pull it once (~2GB download):

```
ollama pull llama3.2
```

Verify the model is ready:
```
ollama list
# Should show: llama3.2
```

Test the model manually:
```
ollama run llama3.2 "How many employees does QAWebPrints have?"
```

### 1.4 How Flask Connects to Ollama

In `backend/app.py`, the LangChain library connects Flask to the local Ollama server:

```python
from langchain_ollama import ChatOllama

def get_llm(model_choice='llama'):
    return ChatOllama(
        model="llama3.2",
        base_url="http://localhost:11434",  # Ollama server address
        temperature=0.3                     # Lower = more factual
    )
```

Every time a user sends a chat message, Flask:
1. Fetches live data from PostgreSQL
2. Builds a prompt with that data
3. Sends the prompt to Ollama via LangChain
4. Returns Ollama's response to the frontend

---

## Part 2 - Database Setup and Connection

### 2.1 Install PostgreSQL

Download from https://www.postgresql.org/download/

During setup:
- Remember the username (default: postgres) and password you set
- Keep the default port: 5432

### 2.2 Create the Database

Open pgAdmin or the psql terminal:

```sql
CREATE DATABASE qa_hr_db;
```

### 2.3 Initialize Tables

After cloning the project and setting up `.env`, run:

```
cd backend
python init_db.py
```

This creates all required tables:
- `users` - employee accounts and roles
- `tasks` - work assignments
- `leaves` - leave requests
- `sessions` - chat history storage

### 2.4 How Flask Connects to PostgreSQL

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

All values come from the `.env` file - never hardcoded.

---

## Part 3 - How the HR Assistant Connects to the Database

This is the most important part. Here is the exact flow:

### Step-by-Step Flow

```
User types: "Who applied for leave?"
         |
         v
Flask /api/chat endpoint receives the message
         |
         v
_fetch_live_company_data(user_id, role) is called
  --> SQL Query 1: SELECT all employees from users table
  --> SQL Query 2: SELECT all tasks from tasks table
  --> SQL Query 3: SELECT all leave requests from leaves table
         |
         v
All SQL results formatted into a readable text block:
  "=== EMPLOYEES ===
   - arjun@qawebprints.com (Role: employee)
   - govindh@gmail.com (Role: manager)
   === LEAVE REQUESTS ===
   - [APPROVED] arjun applied for regular leave on 2026-06-26"
         |
         v
Text is injected into Ollama's system prompt via LangChain:
  SystemMessage: "You are the HR Assistant. Use ONLY the data below..."
  HumanMessage: "Who applied for leave?"
         |
         v
Ollama reads the data and replies:
  "Arjun applied for regular leave on 2026-06-26. Status: Approved."
         |
         v
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

        # Fetch leave requests (column is 'type', not 'leave_type')
        cur.execute("""
            SELECT u.email, l.type, l.start_date, l.end_date, l.reason, l.status
            FROM leaves l JOIN users u ON l.user_id = u.id
        """)
```

### Why This Approach (No Keywords Needed)

- Old approach (broken): AI guesses which function to call, causing hallucinations
- New approach (current): Backend fetches ALL data and gives it directly to Ollama. The AI reads the data and answers. No guessing. No keywords required.

---

## Part 4 - Backend Setup

```
cd backend
python -m venv .venv

# Activate
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # macOS/Linux

pip install -r requirements.txt

copy .env.example .env       # Windows
cp .env.example .env         # macOS/Linux

python init_db.py
python app.py
# Flask API runs on: http://localhost:5000
```

---

## Part 5 - Frontend Setup

```
cd frontend
npm install
npm run dev
# React app runs on: http://localhost:5173
```

---

## Part 6 - Running on a Server

When deploying on a different computer or a Linux server:

### Install All Prerequisites

```
sudo apt install python3 python3-pip python3-venv -y

curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

sudo apt install postgresql postgresql-contrib -y
sudo systemctl start postgresql
sudo systemctl enable postgresql

curl -fsSL https://ollama.com/install.sh | sh
```

### Pull the AI Model

```
ollama pull llama3.2
```

### Clone and Configure

```
git clone https://github.com/ADITHYAN-S-ANIL/qa-hr-assistant.git
cd qa-hr-assistant

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your DB credentials
python3 init_db.py

cd ../frontend
npm install
```

### Run All 3 Services

```
# Terminal 1: Ollama
ollama serve

# Terminal 2: Flask Backend
cd backend && source .venv/bin/activate && python3 app.py

# Terminal 3: Frontend
cd frontend && npm run dev
```

### Run as Permanent Background Services

**Ollama (auto-registered by installer):**
```
sudo systemctl enable ollama
sudo systemctl start ollama
```

**Flask Backend with systemd:**
```
sudo nano /etc/systemd/system/qa-hr-assistant.service
```
```
[Unit]
Description=QA HR Assistant Flask Backend
After=network.target ollama.service

[Service]
WorkingDirectory=/path/to/qa-hr-assistant/backend
ExecStart=/path/to/.venv/bin/python app.py
EnvironmentFile=/path/to/qa-hr-assistant/backend/.env
Restart=always
User=ubuntu

[Install]
WantedBy=multi-user.target
```
```
sudo systemctl enable qa-hr-assistant
sudo systemctl start qa-hr-assistant
```

**Frontend with PM2:**
```
npm install -g pm2
cd frontend
pm2 start "npm run dev" --name qa-frontend
pm2 startup
pm2 save
```

---

## Part 7 - Integrating into an Existing Node.js Portal

If your company already has an HR portal built with Node.js / Express, you do NOT need to replace it. The HR Assistant runs as a **separate microservice** and your Node.js portal connects to it via HTTP.

### 7.1 Architecture Overview

```
Browser (Your Existing Portal)
        |
        | Calls your Node.js portal as usual
        v
Your Node.js / Express Portal  (e.g. port 3000)
        |
        | Proxies /hr-assistant/* requests
        v
Flask HR Assistant Microservice  (port 5000)
        |                    |
        v                    v
  PostgreSQL DB         Ollama AI (port 11434)
```

Your Node.js portal never runs any AI itself. It simply **forwards chat requests** to the Flask service, which handles all AI and database work.

---

### 7.2 Step 1 - Start the Flask HR Assistant

On the same server as your Node.js portal:

```
cd qa-hr-assistant/backend
source .venv/bin/activate    # Linux/macOS
.venv\Scripts\activate       # Windows
python app.py                # Runs on port 5000
```

Also make sure Ollama is running:
```
ollama serve
```

---

### 7.3 Step 2 - Add a Proxy in Your Node.js / Express App

Install the proxy middleware in your **existing** Node.js project:

```
npm install http-proxy-middleware
```

In your Express `server.js` or `app.js`, add:

```javascript
const { createProxyMiddleware } = require('http-proxy-middleware');

// Proxy all /hr-assistant/* requests to Flask on port 5000
app.use('/hr-assistant', createProxyMiddleware({
    target: 'http://localhost:5000',
    changeOrigin: true,
    pathRewrite: {
        '^/hr-assistant': ''    // Strip the /hr-assistant prefix
    },
    on: {
        error: (err, req, res) => {
            res.status(502).json({ error: 'HR Assistant service is unavailable' });
        }
    }
}));

// Your existing routes remain untouched
app.use('/api', yourExistingRouter);
```

Now your portal will automatically forward:
- POST /hr-assistant/api/chat    --> POST http://localhost:5000/api/chat
- GET  /hr-assistant/api/tasks   --> GET  http://localhost:5000/api/tasks
- GET  /hr-assistant/api/leaves  --> GET  http://localhost:5000/api/leaves

---

### 7.4 Step 3 - Bridge Your Login to Get an HR Assistant Token

The Flask service uses its own JWT tokens. When a user logs in to your Node.js portal, also fetch an HR Assistant token:

```javascript
const axios = require('axios');

app.post('/api/login', async (req, res) => {

    // --- Your existing login logic ---
    const user = await YourUserModel.findOne({ email: req.body.email });
    const yourToken = generateYourJWT(user);

    // --- Bridge: Also get an HR Assistant token ---
    let hrToken = null;
    try {
        const hrRes = await axios.post('http://localhost:5000/api/login', {
            email: req.body.email,
            password: req.body.password
        });
        hrToken = hrRes.data.token;
    } catch (e) {
        console.error('HR Assistant login failed:', e.message);
    }

    res.json({
        token: yourToken,     // Your existing portal token
        hr_token: hrToken     // HR Assistant JWT token
    });
});
```

On the frontend, store both tokens when the user logs in:
```javascript
const data = await fetch('/api/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
    headers: { 'Content-Type': 'application/json' }
}).then(r => r.json());

localStorage.setItem('token', data.token);
localStorage.setItem('hr_token', data.hr_token);
```

---

### 7.5 Step 4 - Embed the Chat Widget in Your Existing Portal

Copy the chatbot component from this project into your frontend:
```
qa-hr-assistant/frontend/src/components/Dashboards/FloatingChatbot.jsx
    -->  your-portal/src/components/FloatingChatbot.jsx
```

Then add it to your main layout or dashboard page:
```jsx
import FloatingChatbot from './components/FloatingChatbot';

function DashboardLayout({ children }) {
    const hrToken = localStorage.getItem('hr_token');

    return (
        <div className="layout">
            <YourSidebar />
            <main>{children}</main>

            {/* HR Assistant chatbot - appears as a floating button */}
            {hrToken && <FloatingChatbot apiBase="/hr-assistant" token={hrToken} />}
        </div>
    );
}
```

---

### 7.6 Step 5 - Sending Chat Messages via Raw API Call

If you want to build your own custom chat UI instead of using the widget:

```javascript
async function sendHRMessage(userMessage) {
    const hrToken = localStorage.getItem('hr_token');

    const response = await fetch('/hr-assistant/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${hrToken}`
        },
        body: JSON.stringify({
            message: userMessage,
            session_id: null,       // null = new session
            chat_mode: 'general'
        })
    });

    const data = await response.json();
    return data.reply;    // The AI's response string
}

// Example usage
const answer = await sendHRMessage("How many employees are on leave today?");
// Returns: "1 employee is on approved leave: Arjun (regular leave, 2026-06-26)."
```

---

### 7.7 Running All Services Permanently on a Linux Server

**Ollama (auto-managed by systemd after install):**
```
sudo systemctl enable ollama
sudo systemctl start ollama
```

**Flask HR Assistant as a systemd service:**
```
sudo nano /etc/systemd/system/qa-hr-assistant.service
```
```
[Unit]
Description=QA HR Assistant Flask Microservice
After=network.target ollama.service

[Service]
WorkingDirectory=/path/to/qa-hr-assistant/backend
ExecStart=/path/to/qa-hr-assistant/backend/.venv/bin/python app.py
EnvironmentFile=/path/to/qa-hr-assistant/backend/.env
Restart=always
User=ubuntu

[Install]
WantedBy=multi-user.target
```
```
sudo systemctl enable qa-hr-assistant
sudo systemctl start qa-hr-assistant
```

**Your Node.js Portal (using PM2):**
```
npm install -g pm2
cd your-nodejs-portal
pm2 start server.js --name my-hr-portal
pm2 startup
pm2 save
```

---

### 7.8 Complete Service Summary

| Service             | Port  | Managed By | Purpose                         |
|---------------------|-------|------------|---------------------------------|
| Ollama              | 11434 | systemd    | Runs the AI model locally       |
| Flask HR Assistant  | 5000  | systemd    | AI queries + database access    |
| Your Node.js Portal | 3000  | PM2        | Existing portal (user-facing)   |
| PostgreSQL          | 5432  | systemd    | Employee, task, leave data      |

---

## Environment Variables

Create `backend/.env` from the template:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=qa_hr_db
DB_USER=postgres
DB_PASSWORD=your_password_here

JWT_SECRET_KEY=change_this_to_a_long_random_string

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

WARNING: Never commit `.env` to GitHub. It is listed in `.gitignore`.

---

## Roles and Permissions

| Role     | Dashboard Data Visible               | AI Chatbot Access       |
|----------|--------------------------------------|-------------------------|
| CEO      | All employees, all tasks, all leaves | Full company data       |
| Manager  | Their team's tasks and leaves        | Team-scoped data only   |
| HR       | All employees and leave requests     | HR-scoped data          |
| Employee | Own tasks and own leaves only        | Personal data only      |

---

## Troubleshooting

**Ollama not responding?**
```
curl http://localhost:11434
ollama serve
```

**Model not found?**
```
ollama list
ollama pull llama3.2
```

**Backend cannot connect to database?**
- Check PostgreSQL is running
- Verify DB_PASSWORD in .env matches your PostgreSQL password

**Frontend shows blank page or proxy error?**
- Make sure the Flask backend is running on port 5000
- Check `frontend/vite.config.js` proxy setting points to http://localhost:5000

**AI gives wrong or empty answers?**
- Make sure Ollama is running: `ollama serve`
- Make sure the model is downloaded: `ollama list` should show llama3.2

---

## License
Internal project - QAWebPrints Infocorp LLP. All rights reserved.
