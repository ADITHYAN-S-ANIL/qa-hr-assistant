
import os
import re
import hashlib
import secrets
import requests
import json
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from typing import Any, cast, List, Optional

import jwt
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
# from langchain.chains import RetrievalQA # REPLACING WITH MANUAL LOGIC BELOW

import asyncio
import threading
from langchain_core.messages import ToolMessage

# Thread-local storage so get_leave_status knows which user is asking
_user_context = threading.local()
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("no mcp")

class MCPClient:
    def __init__(self):
        self.tools_cache = []
        self._client = None
        self._loop = None
        self._thread = None
        if not MCP_AVAILABLE:
            return

    def initialize_servers(self, connections_dict: dict):
        if not MCP_AVAILABLE or not connections_dict: return
        
        self._client = MultiServerMCPClient(connections_dict)
        
        # loop for async
        try:
            self._loop = asyncio.get_event_loop_policy().get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
        # get tools
        try:
            self.tools_cache = self._loop.run_until_complete(self._client.get_tools())
            print("tools loaded")
        except Exception as e:
            print("tool err", e)

    def get_lc_tools(self):
        return self.tools_cache

    def invoke_tool(self, tool_name: str, args: dict):
        if not MCP_AVAILABLE: return "MCP not available"
        
        tool = next((t for t in self.tools_cache if t.name == tool_name), None)
        if not tool:
            return f"Error: Tool {tool_name} not found."
            
        try:
            return tool.invoke(args)
        except Exception as e:
            return f"Error executing tool {tool_name}: {e}"



try:
    from pgvector.psycopg2 import register_vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    print("no pgvector")

# load env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# --- Frontend Serving Logic ---
import sys
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# Try to find the dist folder
frontend_folder = get_resource_path("../frontend/dist")
if not os.path.exists(frontend_folder):
    frontend_folder = get_resource_path("dist") # Fallback for bundled state

app = Flask(__name__, static_folder=frontend_folder, static_url_path="")
CORS(app, supports_credentials=True)

@app.route("/")
def serve_index():
    return app.send_static_file("index.html")

@app.errorhandler(404)
def not_found(e):
    # This ensures React Router works (client-side routing)
    return app.send_static_file("index.html")
# ------------------------------

# init mcp
mcp_client = MCPClient() 
mcp_cmd = os.environ.get("MCP_SERVER_CMD")
if mcp_cmd:
    mcp_args = os.environ.get("MCP_SERVER_ARGS", "").split()
    mcp_client.initialize_servers({
        "default": {
            "command": mcp_cmd,
            "args": mcp_args,
            "transport": "stdio"
        }
    })

SECRET_KEY       = os.environ.get("SECRET_KEY", "change-me-in-production")
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")       # primary  (14,400/day free)
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")    # fallback (1,500/day free)
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_SECRET    = os.environ.get("GITHUB_CLIENT_SECRET", "")
FRONTEND_URL     = os.environ.get("FRONTEND_URL", "http://localhost:5173")
TOKEN_EXPIRY_H   = int(os.environ.get("TOKEN_EXPIRY_HOURS", "24"))

# PostgreSQL connection setup
def get_db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "qachat"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASS", "postgres"),
    )

def init_db():
    # PostgreSQL initialization logic is in init_db.py, 
    # so we don't need a complex one here.
    pass

def get_llm(model_choice="llama"):
    from langchain_ollama import ChatOllama
    model_name = "llama3.2:1b" if model_choice == "llama" else "qwen2.5"
    try:
        # Disable GPU (num_gpu=0) to bypass the CUDA crash, and lower context size
        return ChatOllama(model=model_name, num_ctx=1024, num_gpu=0)
    except Exception as e:
        print("Ollama Error:", e)
        return None

# RAG config
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
RAG_TOP_K = 5
RAG_SIMILARITY_THRESHOLD = 0.3

# Use FAISS for RAG (as PGVector is not available on this server)
# But keep PostgreSQL for user/session data
PGVECTOR_AVAILABLE = False
app.config['PGVECTOR_ACTIVE'] = False
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
# ----------------------------------------

# Path variables for local FAISS vector store and training index text file
VECTOR_STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vector_store.faiss")
TEXT_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inata_index.txt")

@tool
def get_leave_status(employee_email: str = None) -> str:
    """
    Fetch leave status (total, taken, and remaining leave).
    If employee_email is provided, fetches the leave status for that specific employee (useful for managers/CEOs).
    If not provided, fetches the leave status of the logged-in user.
    """
    user_id = getattr(_user_context, 'user_id', 1)
    if employee_email:
        try:
            conn = get_db()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT id FROM users WHERE email ILIKE %s", (f"%{employee_email}%",))
                user = cur.fetchone()
                if user:
                    user_id = user['id']
                else:
                    return f"Employee with email {employee_email} not found."
            conn.close()
        except Exception as e:
            return f"Database error looking up employee: {e}"

    try:
        resp = requests.get(f"http://localhost:5001/leave-status?user_id={user_id}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            email_str = f" for {employee_email}" if employee_email else ""
            return (
                f"Leave Status{email_str}: "
                f"Total={data.get('total_leave',30)}, "
                f"Taken={data.get('leave_taken',0)}, "
                f"Remaining={data.get('remaining_leave',30)}"
            )
        return f"API Error: {resp.status_code}"
    except requests.exceptions.ConnectionError:
        return "Leave API is not reachable right now. Please ensure the leave service is running."
    except Exception as e:
        return f"System Error fetching leave: {type(e).__name__}: {e}"

@tool
def get_dashboard_metrics() -> str:
    """Fetch live dashboard metrics: total employees, tasks completed today, and pending leaves. Use this if the user asks for 'total tasks completed' across the company."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE role = 'employee'")
            emp_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM tasks WHERE DATE(created_at) = CURRENT_DATE AND status = 'completed'")
            tasks_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM leaves WHERE status = 'pending'")
            leaves_count = cur.fetchone()[0]
        conn.close()
        return f"Dashboard Summary: Total Employees={emp_count}, Tasks Completed Today={tasks_count}, Pending Leave Requests={leaves_count}"
    except Exception as e:
        return f"Error fetching dashboard metrics: {e}"

@tool
def get_ticket_status(ticket_keyword: str) -> str:
    """Check the status of a specific ticket and see which employees are working on it. Example: ticket_keyword='143'. Do NOT use this to list all 'completed' or 'pending' tasks/tickets; use list_all_tasks for that."""
    if ticket_keyword.strip().lower() in ['completed', 'pending', 'task', 'ticket', 'tasks', 'tickets', 'all']:
        return f"Error: You passed '{ticket_keyword}' as a specific ticket ID. To list all {ticket_keyword} tasks/tickets, you MUST use the list_all_tasks tool instead."
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT t.description, t.status, u.email 
                FROM tasks t 
                JOIN users u ON t.user_id = u.id 
                WHERE t.description ILIKE %s
            """, (f"%{ticket_keyword}%",))
            rows = cur.fetchall()
        conn.close()
        
        if not rows:
            return f"No tasks found matching ticket '{ticket_keyword}'."
            
        lines = [f"Ticket '{ticket_keyword}' Status:"]
        for r in rows:
            lines.append(f"- {r['email']} is working on: '{r['description']}' [Status: {r['status']}]")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching ticket status: {e}"

@tool
def get_employee_tasks(employee_email: str, target_date: str = 'all', current_user_id: int = 1, current_user_role: str = 'ceo') -> str:
    """Fetch the tasks submitted by a specific employee. RBAC enforced."""
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Enforce RBAC
            if current_user_role == 'employee':
                # Can only query themselves
                cur.execute("SELECT id, email FROM users WHERE id = %s", (current_user_id,))
            elif current_user_role == 'manager':
                # Can query themselves or their reports
                cur.execute(
                    """SELECT id, email FROM users 
                       WHERE (email ILIKE %s OR employee_id ILIKE %s) 
                       AND (id = %s OR manager_id = %s) ORDER BY id LIMIT 1""",
                    (f"%{employee_email}%", f"%{employee_email}%", current_user_id, current_user_id)
                )
            else:
                # CEO can query anyone
                cur.execute(
                    "SELECT id, email FROM users WHERE (email ILIKE %s OR employee_id ILIKE %s) ORDER BY id LIMIT 1",
                    (f"%{employee_email}%", f"%{employee_email}%")
                )
                
            user = cur.fetchone()
            if not user:
                return f"Employee '{employee_email}' not found or you do not have permission to view their tasks."

            actual_email = user['email']
            if target_date and target_date != 'all':
                if target_date in ('daily', 'today'):
                    cur.execute(
                        "SELECT description, status, date FROM tasks "
                        "WHERE user_id = %s AND DATE(date) = CURRENT_DATE ORDER BY date DESC",
                        (user['id'],)
                    )
                else:
                    match = re.search(r'(\d{4})[-/](\d{2})[-/](\d{2})', str(target_date))
                    if match:
                        target_date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                        cur.execute(
                            "SELECT description, status, date FROM tasks "
                            "WHERE user_id = %s AND DATE(date) = %s::date ORDER BY date DESC",
                            (user['id'], target_date_str)
                        )
                    else:
                        return f"Error: target_date '{target_date}' is not in YYYY-MM-DD format."
            else:
                cur.execute(
                    "SELECT description, status, date FROM tasks "
                    "WHERE user_id = %s ORDER BY date DESC",
                    (user['id'],)
                )
            tasks = cur.fetchall()
        conn.close()

        if not tasks:
            period_str = f" on {target_date}" if target_date != 'all' else ""
            return f"No tasks found for {actual_email}{period_str}."
            
        completed = [t for t in tasks if t['status'] == 'completed']
        pending = [t for t in tasks if t['status'] == 'pending']
        
        lines = [f"Employee Status:", f"- Name: {actual_email}"]
        if tasks:
            lines.append(f"- Current Task: {tasks[0]['description']}")
            lines.append(f"- Status: {tasks[0]['status'].title()}")
            
        if completed:
            lines.append("- Tasks Completed" + (f" Today:" if target_date != 'all' else ":"))
            for i, t in enumerate(completed, 1):
                lines.append(f"   {i}. {t['description']}")
                
        if pending:
            lines.append("- Pending Tasks:")
            for i, t in enumerate(pending, 1):
                lines.append(f"   {i}. {t['description']}")
                
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching tasks: {e}"


def get_employee_status(name_or_email: str, current_user_id: int, current_user_role: str) -> str:
    """Returns a full status summary for a specific employee. RBAC Enforced."""
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Enforce RBAC
            if current_user_role == 'employee':
                cur.execute("SELECT id, email, employee_id, role FROM users WHERE id = %s", (current_user_id,))
            elif current_user_role == 'manager':
                cur.execute(
                    """SELECT id, email, employee_id, role FROM users 
                       WHERE (email ILIKE %s OR employee_id ILIKE %s) AND (id = %s OR manager_id = %s) ORDER BY id LIMIT 1""",
                    (f"%{name_or_email}%", f"%{name_or_email}%", current_user_id, current_user_id)
                )
            else:
                cur.execute(
                    "SELECT id, email, employee_id, role FROM users WHERE (email ILIKE %s OR employee_id ILIKE %s) ORDER BY id LIMIT 1",
                    (f"%{name_or_email}%", f"%{name_or_email}%")
                )
                
            user = cur.fetchone()
            if not user:
                return f"Employee '{name_or_email}' not found or access denied."

            uid = user['id']
            email = user['email']
            
            cur.execute("SELECT description, status, date FROM tasks WHERE user_id = %s ORDER BY date DESC", (uid,))
            tasks = cur.fetchall()
            
        conn.close()

        completed = [t for t in tasks if t['status'] == 'completed']
        pending = [t for t in tasks if t['status'] == 'pending']
        
        lines = [f"Employee Status:", f"- Name: {email}"]
        if tasks:
            lines.append(f"- Current Task: {tasks[0]['description']}")
            lines.append(f"- Status: {tasks[0]['status'].title()}")
            
        if completed:
            lines.append("- Tasks Completed:")
            for i, t in enumerate(completed[:5], 1):
                lines.append(f"   {i}. {t['description']}")
                
        if pending:
            lines.append("- Pending Tasks:")
            for i, t in enumerate(pending[:5], 1):
                lines.append(f"   {i}. {t['description']}")
                
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching employee status: {e}"


@tool
def list_employees(current_user_id: int = 1, current_user_role: str = 'ceo') -> str:
    """Retrieve a list of employees. RBAC Enforced."""
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if current_user_role == 'employee':
                cur.execute("SELECT email, role, employee_id FROM users WHERE id = %s", (current_user_id,))
            elif current_user_role == 'manager':
                cur.execute("SELECT email, role, employee_id FROM users WHERE id = %s OR manager_id = %s ORDER BY email ASC", (current_user_id, current_user_id))
            else:
                cur.execute("SELECT email, role, employee_id FROM users ORDER BY email ASC")
            rows = cur.fetchall()
        conn.close()
        if not rows:
            return "No employees found."
        return "Employees:\\n" + "\\n".join(f"- {r['email']} (ID: {r['employee_id'] or 'N/A'}, Role: {r['role']})" for r in rows)
    except Exception as e:
        return f"Error listing employees: {e}"

@tool
def list_all_tasks(filter_period: str = 'all', status: str = 'all', current_user_id: int = 1, current_user_role: str = 'ceo') -> str:
    """Retrieve tasks (also called tickets). RBAC enforced. Use this to list all tasks or tickets, or filter them by status (e.g. 'completed', 'pending'). Do NOT use get_ticket_status if the user asks for 'completed tasks' or 'completed tickets'."""
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            clauses = []
            params = []
            
            if current_user_role == 'employee':
                clauses.append("t.user_id = %s")
                params.append(current_user_id)
            elif current_user_role == 'manager':
                clauses.append("(t.user_id = %s OR u.manager_id = %s)")
                params.extend([current_user_id, current_user_id])
                
            if filter_period == 'daily':
                clauses.append("t.date = CURRENT_DATE")
            elif filter_period == 'weekly':
                clauses.append("t.date >= CURRENT_DATE - INTERVAL '7 days'")
                
            if status in ('pending', 'completed'):
                clauses.append("t.status = %s")
                params.append(status)
                
            where_clause = "WHERE " + " AND ".join(clauses) if clauses else ""
            
            cur.execute(f"""
                SELECT t.description, t.status, t.date, u.email 
                FROM tasks t JOIN users u ON t.user_id = u.id 
                {where_clause}
                ORDER BY t.date DESC, t.created_at DESC
            """, params)
            rows = cur.fetchall()
        conn.close()
        if not rows:
            return f"No tasks or tickets found."
        lines = [f"Tasks and Tickets ({filter_period}, status: {status}):"]
        for r in rows:
            name = r['email'].split('@')[0].title()
            lines.append(f"- {name}: {r['description']} [{r['status'].title()}]")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing tasks: {e}"

@tool
def get_jira_ticket_status(ticket_id: str, current_user_id: int = 1, current_user_role: str = 'ceo') -> str:
    """Retrieve the status and employees working on a specific Jira ticket. Do NOT use this to list all 'completed' or 'pending' tasks/tickets; use list_all_tasks instead."""
    if ticket_id.strip().lower() in ['completed', 'pending', 'task', 'ticket', 'tasks', 'tickets', 'all']:
        return f"Error: You passed '{ticket_id}' as a specific ticket ID. To list all {ticket_id} tasks/tickets, you MUST use the list_all_tasks tool instead."
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            clauses = ["t.description ILIKE %s"]
            params = [f"%{ticket_id}%"]
            
            if current_user_role == 'employee':
                clauses.append("t.user_id = %s")
                params.append(current_user_id)
            elif current_user_role == 'manager':
                clauses.append("(t.user_id = %s OR u.manager_id = %s)")
                params.extend([current_user_id, current_user_id])
                
            where_clause = "WHERE " + " AND ".join(clauses)
            
            cur.execute(f"""
                SELECT t.description, t.status, u.email 
                FROM tasks t JOIN users u ON t.user_id = u.id 
                {where_clause}
                ORDER BY t.date DESC
            """, params)
            rows = cur.fetchall()
        conn.close()
        
        if not rows:
            return f"No one is currently working on ticket {ticket_id}."
            
        lines = [f"Employees working on {ticket_id}:"]
        for r in rows:
            name = r['email'].split('@')[0].title()
            lines.append(f"- {name}: {r['description']} [{r['status'].title()}]")
        return "\n".join(lines)
    except Exception as e:
        return f"Error retrieving ticket status: {e}"


@tool
def list_leaves(status: str = 'all', current_user_id: int = 1, current_user_role: str = 'ceo') -> str:
    """Retrieve leave requests. Returns dates, leave type (regular, comp-off, half-day), reason, and status. Use this when asked about leave details or comp-offs."""
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            clauses = []
            params = []
            
            if current_user_role == 'employee':
                clauses.append("l.user_id = %s")
                params.append(current_user_id)
            elif current_user_role == 'manager':
                clauses.append("(l.user_id = %s OR u.manager_id = %s)")
                params.extend([current_user_id, current_user_id])
                
            if status in ('pending', 'approved', 'rejected'):
                clauses.append("l.status = %s")
                params.append(status)
                
            where_clause = "WHERE " + " AND ".join(clauses) if clauses else ""
                
            cur.execute(f"""
                SELECT l.start_date, l.end_date, l.status, l.type, l.reason, u.email, u.id as u_id
                FROM leaves l JOIN users u ON l.user_id = u.id 
                {where_clause}
                ORDER BY l.start_date DESC
            """, params)
            rows = cur.fetchall()
        conn.close()
        if not rows:
            return f"No leave requests found."
            
        lines = ["Yes, the following employees applied for leave:" if status == 'all' else f"Leave Requests ({status}):"]
        for i, r in enumerate(rows, 1):
            lines.append(f"{i}. {r['email'].split('@')[0].title()}")
            lines.append(f"   - Leave Type: {r['type'].title()} Leave")
            if r['start_date'] == r['end_date']:
                lines.append(f"   - Date: {r['start_date']}")
            else:
                lines.append(f"   - Dates: {r['start_date']} to {r['end_date']}")
            if r['reason']:
                lines.append(f"   - Reason: {r['reason']}")
            lines.append(f"   - Status: {r['status'].title()}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing leaves: {e}"

def mark_task_completed(current_user_id: int) -> str:
    """Mark the user's most recent pending task as completed."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tasks SET status = 'completed', updated_at = NOW()
                WHERE id = (
                    SELECT id FROM tasks WHERE user_id = %s AND status = 'pending' 
                    ORDER BY date DESC LIMIT 1
                ) RETURNING description
            """, (current_user_id,))
            res = cur.fetchone()
            conn.commit()
        conn.close()
        if res:
            return f"Successfully marked task '{res[0]}' as completed."
        return "You have no pending tasks to complete."
    except Exception as e:
        return f"Error updating task: {e}"
        
def apply_leave_tomorrow(current_user_id: int, ltype: str = 'regular') -> str:
    """Apply leave for tomorrow."""
    try:
        import datetime
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        conn = get_db()
        with conn.cursor() as cur:
            # Check balance first
            cur.execute("SELECT total_leaves, used_leaves FROM users WHERE id = %s", (current_user_id,))
            u = cur.fetchone()
            if not u:
                return "User not found."
            available = float(u[0] - u[1])
            days = 0.5 if ltype == 'half-day' else 1.0
            if days > available:
                return f"Insufficient leave balance. You requested {days} day(s) but only have {available} day(s) remaining."

            cur.execute("""
                INSERT INTO leaves (user_id, start_date, end_date, status, type, reason)
                VALUES (%s, %s, %s, 'pending', %s, 'Applied via Chatbot')
            """, (current_user_id, tomorrow, tomorrow, ltype))
            conn.commit()
        conn.close()
        return f"Successfully applied for {'half-day ' if ltype == 'half-day' else ''}leave on {tomorrow}. Status is Pending Approval."
    except Exception as e:
        return f"Error applying leave: {e}"

@tool
def search_web(query: str) -> str:
    """Useful to search the internet for real-time information, recent news, or sports results."""
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    try:
        html = urllib.request.urlopen(req, timeout=5).read()
        soup = BeautifulSoup(html, 'html.parser')
        results = ""
        for a in soup.find_all('a', class_='result__snippet'):
            results += a.text + "\n"
        return results[:2000] if results else "No results found."
    except Exception as e:
        return f"Search failed: {e}"

def is_greeting_query(query):
    """Detects pure greetings and casual small talk."""
    greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "good night"]
    casual = ["how are you", "what is this", "who are you", "tell me a joke", "thank you", "thanks", "bye", "okay", "ok"]
    q = query.lower().strip()
    if any(re.search(rf"\b{g}\b", q) for g in greetings):
        return True
    if any(re.search(rf"\b{c}\b", q) for c in casual):
        return True
    return False

def is_leave_query(query):
    """Detects questions specifically about leave balance, taken, or remaining."""
    leave_keywords = ["leave", "leaves", "vacation", "day off", "days off", "time off", "annual leave", "absence", "remaining leave", "leave balance", "leave taken"]
    q = query.lower()
    return any(kw in q for kw in leave_keywords)

def safe_invoke(llm, messages, lc_tools=None):
    try:
        llm_bound = llm.bind_tools(lc_tools) if lc_tools else llm
        return llm_bound.invoke(messages)
    except Exception as e:
        return "I am currently running in local keyword mode and cannot reach the AI API."

def _normalize_query(q: str) -> str:
    """Strip common filler words."""
    import re as _re
    fillers = r'\b(the|a|an|me|please|can|you|i|want|to|for|of|give|fetch|get|show|display|tell|all)\b'
    normalized = _re.sub(fillers, ' ', q, flags=_re.IGNORECASE)
    return _re.sub(r'\s+', ' ', normalized).strip()

def _fetch_leave_direct(user_id: int) -> str:
    import requests
    try:
        r = requests.get(f"http://127.0.0.1:5001/leave-status?user_id={user_id}", timeout=2)
        if r.status_code == 200:
            d = r.json()
            res = f"Leave Balance:\n- Total Leave: {d['total_leave']}\n- Leave Taken: {d['leave_taken']}\n- Remaining leave: {d['remaining_leave']}"
            
            try:
                from app import get_db
                import psycopg2.extras
                conn = get_db()
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT start_date, end_date, status FROM leaves WHERE user_id = %s AND type = 'comp-off' ORDER BY start_date DESC", (user_id,))
                    comp_leaves = cur.fetchall()
                conn.close()
                if comp_leaves:
                    res += "\n- Compensatory Leaves (Comp-off):"
                    for cl in comp_leaves:
                        date_str = f"{cl['start_date']}" if cl['start_date'] == cl['end_date'] else f"{cl['start_date']} to {cl['end_date']}"
                        res += f"\n  * {date_str} ({cl['status'].title()})"
            except Exception:
                pass
                
            return res
        return "Could not fetch leave balance."
    except requests.exceptions.RequestException:
        return "The Leave API is currently offline."


def get_company_dashboard(current_user_role: str, current_user_id: int) -> str:
    """Return top level metrics for CEO or Manager."""
    try:
        from app import get_db
        conn = get_db()
        with conn.cursor() as cur:
            if current_user_role == 'manager':
                cur.execute("SELECT COUNT(*) FROM users WHERE manager_id = %s", (current_user_id,))
                emp_count = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT COUNT(*) FROM tasks t JOIN users u ON t.user_id = u.id 
                    WHERE u.manager_id = %s AND t.date = CURRENT_DATE AND t.status = 'completed'
                """, (current_user_id,))
                tasks_today = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT COUNT(*) FROM tasks t JOIN users u ON t.user_id = u.id 
                    WHERE u.manager_id = %s AND t.status = 'pending'
                """, (current_user_id,))
                pending_tasks = cur.fetchone()[0]

                cur.execute("""
                    SELECT COUNT(*) FROM leaves l JOIN users u ON l.user_id = u.id 
                    WHERE u.manager_id = %s AND CURRENT_DATE >= l.start_date AND CURRENT_DATE <= l.end_date AND l.status = 'approved'
                """, (current_user_id,))
                leaves_today = cur.fetchone()[0]

                cur.execute("""
                    SELECT COUNT(*) FROM leaves l JOIN users u ON l.user_id = u.id
                    WHERE u.manager_id = %s AND l.status = 'pending'
                """, (current_user_id,))
                pending_leaves = cur.fetchone()[0]

                return (
                    f"Manager Team Dashboard:\n"
                    f"- Team Size: {emp_count} employees\n"
                    f"- Tasks Completed Today: {tasks_today}\n"
                    f"- Pending Tasks: {pending_tasks}\n"
                    f"- Team Members on Leave Today: {leaves_today}\n"
                    f"- Pending Leave Requests: {pending_leaves}"
                )

            else:
                # CEO and any other privileged role gets full company-wide view
                cur.execute("SELECT COUNT(*) FROM users WHERE role = 'employee'")
                emp_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM users WHERE role = 'manager'")
                manager_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM users")
                total_users = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM tasks WHERE date = CURRENT_DATE AND status = 'completed'")
                tasks_today = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
                pending_tasks = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM tasks WHERE status = 'in_progress'")
                inprogress_tasks = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM leaves WHERE CURRENT_DATE >= start_date AND CURRENT_DATE <= end_date AND status = 'approved'")
                leaves_today = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM leaves WHERE status = 'pending'")
                pending_leaves = cur.fetchone()[0]

                return (
                    f"Company Dashboard (CEO View):\n"
                    f"--- Workforce ---\n"
                    f"- Total Registered Users: {total_users}\n"
                    f"- Total Employees: {emp_count}\n"
                    f"- Total Managers: {manager_count}\n"
                    f"--- Tasks ---\n"
                    f"- Tasks Completed Today: {tasks_today}\n"
                    f"- Pending Tasks (All): {pending_tasks}\n"
                    f"- In-Progress Tasks: {inprogress_tasks}\n"
                    f"--- Leaves ---\n"
                    f"- Employees on Leave Today: {leaves_today}\n"
                    f"- Pending Leave Requests: {pending_leaves}"
                )

    except Exception as e:
        return f"Error fetching dashboard: {e}"


def get_inactive_employees(current_user_role: str, current_user_id: int) -> str:
    """Find employees with 0 completed tasks today."""
    try:
        from app import get_db
        conn = get_db()
        with conn.cursor() as cur:
            if current_user_role == 'manager':
                cur.execute("""
                    SELECT email FROM users u 
                    WHERE manager_id = %s AND id NOT IN (
                        SELECT user_id FROM tasks WHERE date = CURRENT_DATE AND status = 'completed'
                    )
                """, (current_user_id,))
            elif current_user_role == 'ceo':
                cur.execute("""
                    SELECT email FROM users u 
                    WHERE role = 'employee' AND id NOT IN (
                        SELECT user_id FROM tasks WHERE date = CURRENT_DATE AND status = 'completed'
                    )
                """,)
            else:
                return "Access denied."
            rows = cur.fetchall()
        conn.close()
        if not rows:
            return "All employees have completed at least one task today. Great productivity!"
        return "Employees with NO completed tasks today:\n" + "\n".join(f"- {r[0]}" for r in rows)
    except Exception as e:
        return f"Error fetching inactive employees: {e}"

def get_performance_report(current_user_role: str, current_user_id: int) -> str:
    """List employees sorted by highest number of pending tasks."""
    try:
        from app import get_db
        conn = get_db()
        with conn.cursor() as cur:
            if current_user_role == 'manager':
                cur.execute("""
                    SELECT u.email, COUNT(t.id) as pending_count 
                    FROM users u LEFT JOIN tasks t ON u.id = t.user_id AND t.status = 'pending'
                    WHERE u.manager_id = %s
                    GROUP BY u.email ORDER BY pending_count DESC LIMIT 10
                """, (current_user_id,))
            elif current_user_role == 'ceo':
                cur.execute("""
                    SELECT u.email, COUNT(t.id) as pending_count 
                    FROM users u LEFT JOIN tasks t ON u.id = t.user_id AND t.status = 'pending'
                    WHERE u.role = 'employee'
                    GROUP BY u.email ORDER BY pending_count DESC LIMIT 10
                """,)
            else:
                return "Access denied."
            rows = cur.fetchall()
        conn.close()
        if not rows:
            return "No performance data available."
        return "Employee Performance (Highest Pending Tasks):\n" + "\n".join(f"- {r[0]}: {r[1]} pending tasks" for r in rows)
    except Exception as e:
        return f"Error fetching performance report: {e}"


def get_employee_leave_balance(name_or_email: str, current_user_id: int, current_user_role: str) -> str:
    """Returns the leave balance for a specific employee. RBAC Enforced."""
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if current_user_role == 'employee':
                cur.execute("SELECT id, email, total_leaves, used_leaves FROM users WHERE id = %s", (current_user_id,))
            elif current_user_role == 'manager':
                cur.execute(
                    """SELECT id, email, total_leaves, used_leaves FROM users 
                       WHERE (email ILIKE %s OR employee_id ILIKE %s) AND (id = %s OR manager_id = %s) ORDER BY id LIMIT 1""",
                    (f"%{name_or_email}%", f"%{name_or_email}%", current_user_id, current_user_id)
                )
            else:
                cur.execute(
                    "SELECT id, email, total_leaves, used_leaves FROM users WHERE (email ILIKE %s OR employee_id ILIKE %s) ORDER BY id LIMIT 1",
                    (f"%{name_or_email}%", f"%{name_or_email}%")
                )
            user = cur.fetchone()
            if not user:
                return f"Employee '{name_or_email}' not found or access denied."
            
            cur.execute(
                "SELECT start_date, end_date, status FROM leaves WHERE user_id = %s AND type = 'comp-off' ORDER BY start_date DESC",
                (user['id'],)
            )
            comp_leaves = cur.fetchall()
            
            bal = user['total_leaves'] - user['used_leaves']
            res = f"Leave Balance for {user['email']}:\n- Total Leaves: {user['total_leaves']}\n- Leaves Taken: {user['used_leaves']}\n- Remaining Leaves: {bal}"
            
            if comp_leaves:
                res += "\n- Compensatory Leaves (Comp-off):"
                for cl in comp_leaves:
                    date_str = f"{cl['start_date']}" if cl['start_date'] == cl['end_date'] else f"{cl['start_date']} to {cl['end_date']}"
                    res += f"\n  * {date_str} ({cl['status'].title()})"
            return res
    except Exception as e:
        return f"Error fetching leave balance: {e}"

def get_absent_employees(current_user_role: str, current_user_id: int) -> str:
    """Find employees on approved leave today. RBAC Enforced."""
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if current_user_role == 'employee':
                cur.execute("""
                    SELECT u.email FROM leaves l JOIN users u ON l.user_id = u.id
                    WHERE u.id = %s AND CURRENT_DATE >= l.start_date AND CURRENT_DATE <= l.end_date AND l.status = 'approved'
                """, (current_user_id,))
            elif current_user_role == 'manager':
                cur.execute("""
                    SELECT u.email FROM leaves l JOIN users u ON l.user_id = u.id
                    WHERE (u.manager_id = %s OR u.id = %s) AND CURRENT_DATE >= l.start_date AND CURRENT_DATE <= l.end_date AND l.status = 'approved'
                """, (current_user_id, current_user_id))
            else:
                cur.execute("""
                    SELECT u.email FROM leaves l JOIN users u ON l.user_id = u.id
                    WHERE CURRENT_DATE >= l.start_date AND CURRENT_DATE <= l.end_date AND l.status = 'approved'
                """)
            rows = cur.fetchall()
        conn.close()
        if not rows:
            return "No employees are absent today. Everyone is working!"
        return "Absent Employees (on Approved Leave Today):\n" + "\n".join(f"- {r['email']}" for r in rows)
    except Exception as e:
        return f"Error fetching absent employees: {e}"

def get_leave_status_summary(current_user_role: str, current_user_id: int) -> str:
    """Provides a summary of who is on leave today and leaves applied for upcoming days (RBAC enforced)."""
    try:
        import datetime
        today = datetime.date.today()
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 1. Who is on approved leave today
            if current_user_role == 'employee':
                cur.execute("""
                    SELECT u.email, l.type FROM leaves l JOIN users u ON l.user_id = u.id
                    WHERE u.id = %s AND %s >= l.start_date AND %s <= l.end_date AND l.status = 'approved'
                """, (current_user_id, today, today))
            elif current_user_role == 'manager':
                cur.execute("""
                    SELECT u.email, l.type FROM leaves l JOIN users u ON l.user_id = u.id
                    WHERE (u.manager_id = %s OR u.id = %s) AND %s >= l.start_date AND %s <= l.end_date AND l.status = 'approved'
                """, (current_user_id, current_user_id, today, today))
            else:
                cur.execute("""
                    SELECT u.email, l.type FROM leaves l JOIN users u ON l.user_id = u.id
                    WHERE %s >= l.start_date AND %s <= l.end_date AND l.status = 'approved'
                """, (today, today))
            absent_today = cur.fetchall()

            # 2. Leaves applied for upcoming days (today or future days)
            if current_user_role == 'employee':
                cur.execute("""
                    SELECT l.start_date, l.end_date, l.status, l.type, l.reason, u.email
                    FROM leaves l JOIN users u ON l.user_id = u.id
                    WHERE u.id = %s AND (l.start_date >= %s OR l.end_date >= %s)
                    ORDER BY l.start_date ASC
                """, (current_user_id, today, today))
            elif current_user_role == 'manager':
                cur.execute("""
                    SELECT l.start_date, l.end_date, l.status, l.type, l.reason, u.email
                    FROM leaves l JOIN users u ON l.user_id = u.id
                    WHERE (u.manager_id = %s OR u.id = %s) AND (l.start_date >= %s OR l.end_date >= %s)
                    ORDER BY l.start_date ASC
                """, (current_user_id, current_user_id, today, today))
            else:
                cur.execute("""
                    SELECT l.start_date, l.end_date, l.status, l.type, l.reason, u.email
                    FROM leaves l JOIN users u ON l.user_id = u.id
                    WHERE (l.start_date >= %s OR l.end_date >= %s)
                    ORDER BY l.start_date ASC
                """, (today, today))
            upcoming_leaves = cur.fetchall()
            
        conn.close()

        lines = ["**Leave Status Today:**"]
        if not absent_today:
            lines.append("No one is on leave today.")
        else:
            for r in absent_today:
                name = r['email'].split('@')[0].title()
                lines.append(f"- {name} ({r['type'].title()} Leave)")
        
        lines.append("")
        lines.append("**Leaves Applied for Upcoming Days:**")
        if not upcoming_leaves:
            lines.append("No upcoming leave requests.")
        else:
            for i, r in enumerate(upcoming_leaves, 1):
                name = r['email'].split('@')[0].title()
                lines.append(f"{i}. {name}: {r['start_date']} to {r['end_date']}")
                lines.append(f"   - Type: {r['type'].title()} Leave | Status: {r['status'].title()}")
                if r['reason']:
                    lines.append(f"   - Reason: {r['reason']}")
                lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting leave status summary: {e}"

def get_present_employees(current_user_role: str, current_user_id: int) -> str:
    """Find employees present today (not on approved leave). RBAC Enforced."""
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT user_id FROM leaves 
                WHERE CURRENT_DATE >= start_date AND CURRENT_DATE <= end_date AND status = 'approved'
            """)
            absent_ids = [r['user_id'] for r in cur.fetchall()]
            
            if current_user_role == 'employee':
                cur.execute("SELECT id, email FROM users WHERE id = %s", (current_user_id,))
            elif current_user_role == 'manager':
                cur.execute("SELECT id, email FROM users WHERE manager_id = %s OR id = %s", (current_user_id, current_user_id))
            else:
                cur.execute("SELECT id, email FROM users WHERE role = 'employee'")
            users = cur.fetchall()
        conn.close()
        
        present = [u['email'] for u in users if u['id'] not in absent_ids]
        if not present:
            return "No employees are present today."
        return "Present Employees (Working Today):\n" + "\n".join(f"- {email}" for email in present)
    except Exception as e:
        return f"Error fetching present employees: {e}"


def _keyword_fast_path(q_lower: str, query_text: str, user_id: int, user_role: str = 'employee'):
    """
    Advanced NLP routing engine supporting intents and RBAC.
    """
    import re as _re

    q_norm = _normalize_query(q_lower)

    def matches(kws):
        return any(kw in q_norm or kw in q_lower for kw in kws)

    def _clean_search_name(n: str) -> str:
        emails = _re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-.]+', n)
        if emails:
            return emails[0].strip()
        for word in ["the", "today", "yesterday", "employee", "staff", "worker", "id", "emp"]:
            n = _re.sub(rf"\b{word}\b", " ", n, flags=_re.IGNORECASE)
        return _re.sub(r"\s+", " ", n).strip()

    # 0.5 Ticket Lookup
    p_ticket_match = _re.search(r'(?:jira\s+ticket|jira\s+issue|ticket|issue|jira|bug|task|story|epic|defect|pr|pull\s+request|incident|request|patch|hotfix|feature|chore|fix|enhancement|subtask|release|deploy|support|vulnerability|upgrade|update|migration|maintenance|outage|test|qa|doc|documentation|sprint|backlog|milestone|initiative|theme|pipeline|build|investigation|spike|refactor|audit|review|optimization)\s+([a-zA-Z0-9-]+)', q_lower)
    if p_ticket_match:
        ticket_id = p_ticket_match.group(1).strip()
        if ticket_id not in ("list", "status", "updates", "report", "progress", "history", "number", "id", "ticket", "issue", "bug", "task", "story", "epic", "defect", "pr", "incident", "request", "patch", "hotfix", "feature", "chore", "fix", "enhancement", "subtask", "release", "deploy", "support", "vulnerability", "upgrade", "update", "migration", "maintenance", "outage", "test", "qa", "doc", "documentation", "sprint", "backlog", "milestone", "initiative", "theme", "pipeline", "build", "investigation", "spike", "refactor", "audit", "review", "optimization"):
            return get_jira_ticket_status.invoke({"ticket_id": ticket_id, "current_user_id": user_id, "current_user_role": user_role})

    # 1. Attendance / Presence / Absentees
    absent_kws = [
        "absent", "who is absent", "employees are absent", "anyone absent", "no one absent", 
        "who is off today", "who is away today", "absent employees", "which employees are absent",
        "anyone absent today", "nobody absent", "no one absent",
        "who's out today", "who's absent", "who is not in today", "who didn't show up", "who is off", 
        "who's off", "list of absentees", "missing employees", "is anyone off today", 
        "who is out", "who is not here", "anyone not working today", "who is not present", "not in today",
        "employees on leave", "absentees", "who is out of the office", "who is out of office", 
        "who's out of office", "out of office list", "not working today", "missing from work", 
        "not here today", "who is missing", "absent list", "people on leave", "who has taken leave today", 
        "list of absent employees", "who didn't login today", "did anyone not login today", 
        "who has not logged in today", "not logged in today", "who is away", "is anyone away today",
        "absent list today", "who is out of office now", "who is off-duty today", "off-duty employees",
        "who didn't come to work", "who skipped work", "who is not online today", "who hasn't checked in",
        "who is not in the office", "who is missing today", "who is absent now", "which staff is absent",
        "who hasn't logged in", "who has off today", "who didn't check in today", "absent roster"
    ]
    if matches(absent_kws):
        return get_absent_employees(user_role, user_id)

    present_kws = [
        "present", "attendance", "login", "online", "working today", "checked in", "logged in", 
        "attendance status", "who logged in", "employees are online", "attendance report", 
        "who is present", "is everyone working", "who logged in today", "checked in today",
        "who is in", "who is working", "who's present", "who's online", "who's working today",
        "is everyone here", "attendance sheet", "active employees", "who is online right now",
        "who is checked in", "employees working today", "who are present", "who is active today",
        "who is checked-in", "who logged-in", "list of present employees", "present list", 
        "who is in the office today", "who came to work today", "who is in today", "logged-in employees", 
        "employees logged in", "checked-in employees", "who is active now", "who is currently active", 
        "online users", "active staff", "who is online today", "who has checked in", "is everyone present today", 
        "who are working right now", "working right now",
        "present staff list", "online workers", "who checked in this morning", "active staff today",
        "who logged in this morning", "who is working right now", "attendance register", "who checked-in today",
        "checked in employees list", "who is on duty today", "who is currently online", "who came in today",
        "who is at work today", "active users list", "who logged-in today", "present team members"
    ]
    if matches(present_kws):
        return get_present_employees(user_role, user_id)

    # 2. CEO/Manager Dashboards / Summaries
    dashboard_kws = [
        "dashboard", "metrics", "company stats", "how many employees", "total employee", "hr summary",
        "how is the company doing", "daily report", "executive summary", "company dashboard", "company metrics",
        "team metrics", "team dashboard", "how's the company doing", "business health", "company summary",
        "business metrics", "performance dashboard", "hr overview", "manager dashboard", "executive dashboard",
        "employee count", "number of employees", "how many workers", "total workers", "total staff",
        "staff size", "status updates", "daily update", "daily updates", "today's report", "today report",
        "today's employee summary", "what happened today in the company", "what happened today",
        "give me a company summary", "company status", "corporate summary", "firm metrics", "how many users are registered",
        "employee statistics", "overall stats", "team updates", "brief summary", "stats overview",
        "give me updates", "how is the team doing", "company overview", "organization overview",
        "organization stats", "general overview", "system status", "tell me about the company status",
        "business overview", "management summary", "team performance dashboard", "performance overview",
        "company report", "overall team summary", "brief me on company metrics", "tell me company stats",
        "firm health", "how are we doing", "business update", "company metrics dashboard", "metrics dashboard",
        "how many registered employees", "total employee count", "staff count", "headcount",
        "firm health metrics", "corporate metrics overview", "company stats report", "give me the daily stats",
        "performance overview metrics", "stats summary", "organizational metrics", "business health check",
        "team performance report", "daily organization updates", "firm status dashboard", "company-wide statistics",
        "firm summary dashboard", "organization report", "business metrics overview", "headcount summary",
        # Manager-count queries (were hallucinating)
        "how many managers", "number of managers", "manager count", "total managers", "how many manager",
        "managers do we have", "how many management", "count of managers", "how many people manage",
        # User/total-count queries
        "how many users", "total users", "user count", "how many people in the company",
        "how many people are registered", "registered users", "total registered",
        # Registered users
        "how many accounts", "total accounts",
    ]
    if matches(dashboard_kws):
        return get_company_dashboard(user_role, user_id)
        
    # 3. Inactive / Slacking
    inactive_kws = [
        "inactive", "no completed tasks", "not completed any work", "doing nothing", "slacking off",
        "is anyone slacking off", "anyone slacking", "who is slacking", "slacking", "slackers", "slacker",
        "is anyone inactive", "inactive employees", "inactive workers", "inactive staff", "who is inactive",
        "anyone inactive", "who did nothing", "did nothing", "doing no work", "who hasn't worked",
        "who has not completed tasks", "zero tasks completed", "no progress", "who is not working properly",
        "who is free", "any employee inactive", "nobody completed tasks",
        "not doing anything", "idle employees", "who is idle", "who has no work", "who is sitting idle", 
        "who didn't do anything", "who is not doing anything", "idle workers", "unassigned employees", 
        "who has no tasks", "who's slacking", "slacking employees", "doing no tasks", "lazy employees",
        "who did not work", "no work done", "who has zero tasks completed", "who is not productive today", 
        "unproductive employees", "unproductive workers", "who has no progress today", "who has not finished any tasks", 
        "who hasn't completed anything", "employees doing nothing", "idle staff", "slacking staff", 
        "who hasn't worked today", "unproductive team members", "who has zero progress", "who is not working today", 
        "who did not do any tasks",
        "doing zero work today", "who did not complete a single task", "idle team members", "unproductive list",
        "who is not active today", "who is currently idle", "sitting idle at work", "who has completed zero work today",
        "who has no completed tasks today", "inactive team members", "slacking workers", "doing absolutely nothing today",
        "who hasn't completed any work today", "who hasn't completed any tasks today", "zero tasks completed list"
    ]
    if matches(inactive_kws):
        return get_inactive_employees(user_role, user_id)
        
    # 4. Performance / Productivity / Overloaded / Bottlenecks
    performance_kws = [
        "performance report", "highest number of pending", "productivity", "bottlenecks", "overloaded with work",
        "performance", "productivity report", "productivity summary", "employee performance", "staff performance",
        "who is overloaded", "overloaded employees", "workload", "workload summary", "pending tasks report",
        "who has most pending", "bottleneck", "efficiency", "output", "target completion", "best employee",
        "low performance", "high performer", "work efficiency", "who performed best", "completed most tasks",
        "low-performing employees", "which employees are overloaded", "which employee is behind schedule",
        "behind schedule", "who completed maximum tasks",
        "workload distribution", "employee productivity", "who is lagging behind", "performance metrics", 
        "bottleneck analysis", "who has too many tasks", "who is struggling", "workload status", 
        "top performers", "low performers", "who is performing poorly", "overloaded team members",
        "employee performance analysis", "productivity analysis", "workload tracker", "workload distribution report", 
        "efficiency report", "efficiency metrics", "who has highest pending tasks", "employees with most pending tasks", 
        "bottleneck report", "who has too much work", "who is overworked", "overworked employees", 
        "overloaded workers", "who completed the most work", "highest performing employees", "who is performing the best", 
        "who is behind on work",
        "overburdened employees", "who has the largest backlog", "backlog report", "most pending work list",
        "struggling team members", "who has too many pending tasks", "performance bottlenecks", "low productivity list",
        "overburdened staff", "efficiency summary", "employee output report", "workload analysis",
        "who is lagging today", "lagging team members", "who is overloaded with tasks", "work overload report"
    ]
    if matches(performance_kws):
        return get_performance_report(user_role, user_id)


    # 5. Intents: Actions (Write operations)
    complete_task_kws = [
        "mark task as completed", "mark work as completed", "finish task", "done with my work",
        "cross my task off", "mark it done", "cross it off", "completed my task",
        "finished my task", "done with task", "mark task done",
        "mark my task as completed", "mark my task completed", "set task as completed", "finish my work",
        "work is done", "finished task",
        "complete my task", "task is completed", "i have finished my task", "completed task", 
        "mark task as done", "done with my tasks", "close my task", "resolve task", "task done", 
        "i completed my task", "close task", "complete task", "finish work", "mark my work as done", 
        "mark task complete", "i finished my task", "i have completed my work", "set task status to completed", 
        "mark my task complete", "mark tasks complete", "mark my tasks as completed", "i am done with my task", 
        "done with work", "resolve my task", "close my pending task", "task finished", "finish task today", 
        "completed task today",
        "mark my daily task done", "set task done", "i finished my work today", "completed today's task",
        "mark as completed", "finish my assigned task", "set task status to done", "mark task completed today",
        "mark my task as finished", "task is finished today", "finished my work for today", "i'm done with my task",
        "mark task finished", "set status of task to completed", "completed my task today", "cross task off my list"
    ]
    if matches(complete_task_kws):
        return mark_task_completed(user_id)
        
    apply_half_day_leave_kws = [
        "apply half-day leave for tomorrow", "apply half day leave tomorrow", "apply half-day leave tomorrow",
        "apply half day leave", "apply half-day leave", "request half day leave", "request half-day leave",
        "request half day leave tomorrow", "request half-day leave tomorrow", "need half day off",
        "need half-day off", "half day off tomorrow", "half-day off tomorrow",
        "book half-day leave", "book half day leave tomorrow", "take half day off tomorrow",
        "requesting half day off tomorrow", "half-day leave request", "submit half day leave",
        "apply for 0.5 leaves tomorrow", "want a half day off tomorrow", "half day off request tomorrow",
        "can i take half day tomorrow", "need half day off tomorrow", "half day tomorrow",
        "take half day tomorrow", "request half day off", "book a half day leave"
    ]
    if matches(apply_half_day_leave_kws):
        return apply_leave_tomorrow(user_id, ltype='half-day')

    apply_leave_kws = [
        "apply leave for tomorrow", "apply leave", "need a vacation", "book time off",
        "apply for leave", "request leave", "request vacation", "take tomorrow off", "take leave tomorrow",
        "apply leave tomorrow", "i need tomorrow off", "applying for leave", "submit leave request",
        "request time off", "book leave",
        "i want to apply for leave", "taking leave tomorrow", "request day off", "off tomorrow", 
        "out of office tomorrow", "book off tomorrow", "i need leave tomorrow", "take a day off tomorrow",
        "request leave for tomorrow", "need a day off", "want to take leave", "apply leave tomorrow", 
        "apply vacation tomorrow", "apply for leave tomorrow", "request leave tomorrow", "i want to take tomorrow off", 
        "requesting leave for tomorrow", "requesting tomorrow off", "i need a day off tomorrow", 
        "book leave for tomorrow", "submit leave request for tomorrow", "applying for leave tomorrow", 
        "i want to apply leave tomorrow", "can I take leave tomorrow", "i need to take leave tomorrow", "taking tomorrow off",
        "apply for vacation tomorrow", "apply for leaves tomorrow", "request holiday tomorrow", "take time off tomorrow",
        "book leaves tomorrow", "submit time off request", "i need a vacation tomorrow", "applying vacation tomorrow",
        "need tomorrow off from work", "take a leave tomorrow", "i want to book leave tomorrow", "request vacation tomorrow",
        "book holiday tomorrow", "register leave for tomorrow", "request time-off tomorrow", "leave application for tomorrow"
    ]
    if matches(apply_leave_kws):
        return apply_leave_tomorrow(user_id)

    # 6. Specific employee leaves (e.g. John's leave balance, remaining leave for Alex)
    p_leaves = _re.search(
        r'(?:leave balance of|leaves remaining for|leave status of|leave staus of|leaves of|leave requests of|leave history of|leave of|remaining leaves for|leaves left for|days off for|vacation status of|vacation of)\s+([a-zA-Z0-9_.@\'-]+(?:\s+[a-zA-Z0-9_.@\'-]+)?)',
        q_lower
    )
    p_leaves_possessive = _re.search(
        r'([a-zA-Z0-9_.@\'-]+(?:\s+[a-zA-Z0-9_.@\'-]+)?)\'s\s+(?:leave balance|leave status|leave staus|leave history|leave requests|leaves|vacation|days off)',
        q_lower
    )
    p_leaves_does_have = _re.search(
        r'(?:how many leaves does|how many leaves has|how much leave does|how many days off does)\s+([a-zA-Z0-9_.@\'-]+(?:\s+[a-zA-Z0-9_.@\'-]+)?)\s+(?:have|has|left|remaining)',
        q_lower
    )
    m_leave = p_leaves or p_leaves_possessive or p_leaves_does_have
    if m_leave:
        name = _clean_search_name(m_leave.group(1))
        if name:
            if name in ("anyone", "someone", "somebody", "anybody", "everyone", "everybody", "employee", "employees"):
                status = "pending" if "pending" in q_lower else "all"
                return list_leaves.invoke({"status": status, "current_user_id": user_id, "current_user_role": user_role})
            return get_employee_leave_balance(name, current_user_id=user_id, current_user_role=user_role)

    # 7. Leave Balance (Self query)
    personal_leave_balance_kws = [
        "my leave balance", "leaves are remaining", "out of leave days", "how many leave",
        "remaining leave", "leave balance", "my remaining leaves", "how many leaves do i have",
        "how many leaves left", "how many leave days", "leaves left", "vacation balance",
        "vacation days left", "how many leaves are remaining", "how much leave", "leave history",
        "leave count", "leave details", "leave report",
        "how many days off do i have", "my leaves left", "how many leaves remaining", 
        "check my leave balance", "what's my leave balance", "remaining leaves", "available leaves", 
        "my available leave", "remaining vacation", "my remaining vacation days", "how much leave balance do i have", 
        "what is my leave balance", "check leave balance", "what's my remaining leave", "how many annual leaves do i have", 
        "check remaining leaves", "my available leaves", "show leave details", 
        "how many leaves can i take", "check vacation balance", "what is my vacation balance", 
        "how many holidays do i have left", "my remaining leave balance", "my leave status",
        "my leave staus", "check my leave", "leaves count", "available leaves balance", "vacation days remaining",
        "how many days off do i have left", "staus of my leave", "remaining leave count",
        "remaining holiday balance", "my remaining vacation", "available leave balance", "my holiday balance"
    ]
    if matches(personal_leave_balance_kws):
        return _fetch_leave_direct(user_id)

    general_leave_status_kws = [
        "leave status", "leave staus", "leaves staus", "staus of leave", "leave status today", "leave staus today"
    ]
    if matches(general_leave_status_kws):
        return get_leave_status_summary(user_role, user_id)
        
    # 8. Generic Leave Requests / Who is on Leave
    leave_requests_kws = [
        "applied for leave", "applied leave", "apply leave today", "on leave", "leave requests",
        "leave requests pending", "who is on leave", "away today", "who's off", "is anyone on leave",
        "is anyone away", "is anyone off", "anyone on leave", "anyone away", "anyone off",
        "anyone applied for leave", "anyone applied leave", "anyone on vacation", "is anyone on vacation",
        "pending leaves", "approved leaves", "list leaves", "show leaves", "leave list", "pending approvals",
        "who applied for leave", "has anyone applied for leave", "any leave requests today",
        "show pending leave requests",
        "who is on vacation", "pending vacation requests", "vacation list", "who is taking leave", 
        "leaves pending approval", "who has taken leave today", "who's on leave today",
        "list of leaves", "leave status updates", "any leave requests", "leave updates", 
        "any leave updates", "leave update", "any leave update", "pending leave requests list", 
        "approved leave requests", "who requested leave", "list of leave requests", "any pending leave requests", 
        "show me leave requests", "who applied for vacation", "list of vacation requests", "leaves updates list", 
        "leave request updates", "who is on holiday today", "who has applied for leave today", 
        "are there any leave requests", "who is on leave now",
        "leave applications list", "who requested vacation", "leaves pending approval",
        "any leave updates today", "vacation requests list", "leave log", "leaves tracking", "history of leaves",
        "leave roster", "who is out today on leave", "who applied for time off", "leaves pending list"
    ]
    if matches(leave_requests_kws):
        status = "pending" if "pending" in q_lower or "pending" in q_norm else "all"
        return list_leaves.invoke({"status": status, "current_user_id": user_id, "current_user_role": user_role})

    # 9. Employees List
    list_employees_kws = [
        "list employee", "list employees", "show employees", "who are employees", "all employees",
        "employees list", "list worker", "list workers", "list staff", "show staff", "show workers",
        "show employee", "who works here", "list of employees", "all the employee",
        "get list of employees", "who are our team members", "show team", "list team", 
        "who is in the team", "roster", "employee directory", "staff directory", "active employees list",
        "list all employees", "show all employees", "list the employees", "list workers", "who are the employees", 
        "show me the employees", "show directory", "who works in the company", "who is in our company", 
        "employees directory", "employee roster", "list of staff", "show me list of employees", "who are our employees",
        "workforce directory", "people in the company", "who is working in this company", "team directory",
        "staff directory roster", "active workforce list", "show all workforce", "list all workers"
    ]
    if matches(list_employees_kws):
        return list_employees.invoke({"current_user_id": user_id, "current_user_role": user_role})

    # 10. Tasks (Self vs Others vs All)
    my_tasks_kws = [
        "my tasks", "my completed work", "on my plate", "to-do list", "todo list",
        "my pending tasks", "what are my tasks", "what is on my plate", "tasks assigned to me",
        "my work", "what do i need to do", "what are my jobs", "my to-do", "my checklist",
        "what should i do today", "tasks to do", "what's my work today", "my task updates", 
        "what's on my to-do list", "my task list", "tasks for me", "what tasks do i have",
        "my tasks for today", "show my tasks for today", "list my tasks", "my to-do list", 
        "my checklist today", "what is my to-do list", "what is assigned to me", "my tasks list", 
        "show my pending tasks", "what tasks are assigned to me today", "my work updates", 
        "my job list", "what are my items",
        "my todo items", "tasks assigned to me today", "my agenda today", "agenda list", "my items",
        "work assigned to me", "my task details", "my pending work list", "what are my assignments"
    ]
    if matches(my_tasks_kws):
        status = "completed" if "completed" in q_lower or "completed" in q_norm else "all"
        return list_all_tasks.invoke({"filter_period": 'all', "status": status, "current_user_id": user_id, "current_user_role": 'employee'})
        
    unfinished_tasks_kws = [
        "unfinished tasks", "didn't finish task", "pending tasks", "pending task",
        "unfinished work", "what tasks are pending", "incomplete tasks", "incomplete work",
        "still pending", "list pending tasks", "show pending tasks", "incomplete", "unfinished",
        "backlog", "incomplete tasks", "due tasks", "missed deadline", "missed deadlines",
        "did anyone not finish assigned work", "did anyone not finish",
        "who didn't complete their tasks", "whose task is pending", "what tasks are left", 
        "uncompleted tasks", "tasks not completed", "who is behind on tasks", "unresolved tasks",
        "list incomplete tasks", "pending updates", "work not completed", "uncompleted work",
        "who has pending tasks", "list all pending tasks", "show incomplete tasks", "what is pending", 
        "which tasks are unfinished", "who has unfinished work", "unfinished tasks report", 
        "pending tasks list", "list of unfinished tasks", "work still in progress", "what tasks are not finished", 
        "tasks still pending", "who didn't finish their tasks today", "did anyone not finish their work today",
        "backlog tasks", "tasks not complete", "incomplete assignments", "list of pending tasks",
        "outstanding work", "remaining tasks list", "tasks still in progress", "uncompleted assignments",
        "which tasks are still pending", "work backlog list", "who still has pending tasks today"
    ]
    if matches(unfinished_tasks_kws):
        return list_all_tasks.invoke({"filter_period": 'all', "status": 'pending', "current_user_id": user_id, "current_user_role": user_role})
        
    completed_tasks_kws = [
        "completed their work", "work done by", "task completed", "tasks completed",
        "completed task", "completed tasks", "who completed work", "finished tasks",
        "tasks finished", "who finished their tasks", "show completed tasks", "list completed tasks",
        "finished work", "what work has been done", "completed assignments", "what tasks did",
        "who has finished their work", "tasks completed today", "who did tasks", "what got done today", 
        "completed tasks report", "who completed their tasks", "who completed tasks today",
        "list of completed tasks", "show all completed tasks", "who has completed tasks", 
        "what tasks are completed today", "tasks finished today", "which tasks were completed today", 
        "who finished work today", "completed work updates", "list finished tasks", 
        "completed assignments report", "work done report", "who completed most tasks today",
        "list of finished tasks", "completed tasks list", "done tasks", "who finished their work today",
        "who has completed work today", "finished assignments today", "who completed their tasks today"
    ]
    if matches(completed_tasks_kws):
        period = 'daily' if 'today' in q_lower or 'today' in q_norm else 'all'
        return list_all_tasks.invoke({"filter_period": period, "status": 'completed', "current_user_id": user_id, "current_user_role": user_role})
        
    all_tasks_kws = [
        "today's employee updates", "show all work", "show all pending tasks", "list task",
        "list tasks", "all tasks", "today status", "employee updates", "employee tasks",
        "all employee tasks", "tasks for today", "today's tasks", "what is everyone doing",
        "what is anyone doing", "work status", "task list", "show all tasks", "list all tasks",
        "task update", "task updates", "show task updates", "list task updates", "update of tasks",
        "show work progress", "work progress", "employee progress", "tell me employee updates",
        "give quick status of all employees", "what are employees doing",
        "show tasks list", "what is the current status of all tasks", "give me an update on tasks", 
        "task details", "current tasks progress", "all updates", "work status updates",
        "all employee tasks updates", "general tasks report", "show task list", "employee task updates", 
        "work status report", "updates of tasks", "work status of employees", "status of all tasks", 
        "show all tasks status", "list of all tasks", "list all employee tasks", "progress report of tasks", 
        "what did everyone do today",
        "current tasks progress", "tasks updates list", "general status of all tasks", "what did anyone do today",
        "overall task status", "work updates roster", "daily task status report", "show all task updates"
    ]
    if matches(all_tasks_kws):
        period = 'daily' if 'today' in q_lower or 'today' in q_norm else 'all'
        return list_all_tasks.invoke({"filter_period": period, "status": 'all', "current_user_id": user_id, "current_user_role": user_role})

    # 11. Specific Employee Lookup (Active Voice)
    p2 = _re.search(
        r'(?:what\s+)?(?:did|has|have|didi|is|was)\s+([a-zA-Z0-9_.@\'-]+(?:\s+[a-zA-Z0-9_.@\'-]+)?)\s+(?:do|done|submit|submitted|work|worked|complete|completed|accomplish|accomplished|any work|working on|finish|finished)',
        q_lower
    )
    if p2:
        raw_name = p2.group(1).strip()
        is_completed_query = any(w in q_lower for w in ["complete", "completed", "done", "finished", "accomplish", "accomplished"])
        status = 'completed' if is_completed_query else 'all'
        if raw_name in ("anyone", "someone", "somebody", "anybody", "everyone", "everybody", "employee", "employees"):
            return list_all_tasks.invoke({"filter_period": 'daily' if 'today' in q_lower else 'all', "status": status, "current_user_id": user_id, "current_user_role": user_role})
        
        name = _clean_search_name(raw_name)
        if name:
            return get_employee_tasks.invoke({"employee_email": name, "target_date": 'daily' if 'today' in q_lower else 'all', "current_user_id": user_id, "current_user_role": user_role})
            
    # 12. Specific Employee Lookup (Passive Voice)
    p_passive = _re.search(
        r'(?:tasks|work|updates|status|todo|assignments)\s+(?:(?:were|are|was|is)\s+)?(?:completed|done|submitted|worked|assigned|todo|pending|finished)\s+(?:by|for|of)\s+([a-zA-Z0-9_.@\'-]+(?:\s+[a-zA-Z0-9_.@\'-]+)?)',
        q_lower
    )
    if p_passive:
        raw_name = p_passive.group(1).strip()
        is_completed_query = any(w in q_lower for w in ["complete", "completed", "done", "finished", "accomplish", "accomplished"])
        status = 'completed' if is_completed_query else 'all'
        if raw_name in ("anyone", "someone", "somebody", "anybody", "everyone", "everybody", "employee", "employees"):
            return list_all_tasks.invoke({"filter_period": 'daily' if 'today' in q_lower else 'all', "status": status, "current_user_id": user_id, "current_user_role": user_role})
        
        name = _clean_search_name(raw_name)
        if name:
            return get_employee_tasks.invoke({"employee_email": name, "target_date": 'daily' if 'today' in q_lower else 'all', "current_user_id": user_id, "current_user_role": user_role})

    # 13. Specific Employee Status or General Activity Lookup
    p_status = _re.search(
        r'(?:status of|tasks are assigned to|doing|working on|progress of|work report of|work summary of|tasks completed by|tasks did|tasks of|work of|productivity of|performance of)\s+([a-zA-Z0-9_.@\'-]+(?:\s+[a-zA-Z0-9_.@\'-]+)?)',
        q_lower
    )
    if p_status:
        raw_name = p_status.group(1).strip()
        if raw_name in ("anyone", "someone", "somebody", "anybody", "everyone", "everybody", "employee", "employees"):
            return list_all_tasks.invoke({"filter_period": 'all', "status": 'all', "current_user_id": user_id, "current_user_role": user_role})
        
        name = _clean_search_name(raw_name)
        if name:
            return get_employee_status(name, current_user_id=user_id, current_user_role=user_role)

    # 14. Jira Ticket lookup (Moved to 10.5)

    # Fallback to LLM / Default Help
    return None

def _fetch_live_company_data(user_id: int, user_role: str) -> str:
    """
    Fetch a complete snapshot of live company data from the DB based on role.
    Each section is fetched independently so one failure doesn't drop the rest.
    """
    lines = []
    conn = None
    try:
        conn = get_db()

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # --- COMPANY INFO (hardcoded, no table needed) ---
            lines.append("Company Name: QAWebPrints Infocorp LLP")

            # --- EMPLOYEES ---
            try:
                lines.append("\n=== EMPLOYEES ===")
                if user_role == 'manager':
                    cur.execute("""
                        SELECT email, role, employee_id FROM users
                        WHERE id = %s OR manager_id = %s ORDER BY email ASC
                    """, (user_id, user_id))
                else:
                    cur.execute("SELECT email, role, employee_id FROM users ORDER BY email ASC")
                employees = cur.fetchall()
                role_counts = {}
                for e in employees:
                    role_counts[e['role']] = role_counts.get(e['role'], 0) + 1
                    lines.append(f"- {e['email']} (ID: {e['employee_id'] or 'N/A'}, Role: {e['role']})")
                for r, c in role_counts.items():
                    lines.append(f"Total {r.capitalize()}s: {c}")
                lines.append(f"Total Registered Users: {len(employees)}")
            except Exception as e:
                lines.append(f"[Employee data error: {e}]")

            # --- TASKS ---
            try:
                lines.append("\n=== TASKS ===")
                if user_role in ('ceo', 'hr'):
                    cur.execute("""
                        SELECT u.email, t.description, t.status, t.date
                        FROM tasks t JOIN users u ON t.user_id = u.id
                        ORDER BY t.date DESC LIMIT 50
                    """)
                elif user_role == 'manager':
                    cur.execute("""
                        SELECT u.email, t.description, t.status, t.date
                        FROM tasks t JOIN users u ON t.user_id = u.id
                        WHERE u.manager_id = %s ORDER BY t.date DESC LIMIT 30
                    """, (user_id,))
                else:
                    cur.execute("""
                        SELECT u.email, t.description, t.status, t.date
                        FROM tasks t JOIN users u ON t.user_id = u.id
                        WHERE t.user_id = %s ORDER BY t.date DESC LIMIT 20
                    """, (user_id,))
                tasks = cur.fetchall()
                status_counts = {}
                for t in tasks:
                    status_counts[t['status']] = status_counts.get(t['status'], 0) + 1
                    lines.append(f"- [{t['status'].upper()}] {t['email']}: {t['description']} (Date: {t['date']})")
                for s, c in status_counts.items():
                    lines.append(f"Total {s} tasks: {c}")
                if not tasks:
                    lines.append("No tasks found.")
            except Exception as e:
                lines.append(f"[Task data error: {e}]")

            # --- LEAVE REQUESTS ---
            try:
                lines.append("\n=== LEAVE REQUESTS ===")
                if user_role in ('ceo', 'hr'):
                    cur.execute("""
                        SELECT u.email as applicant, l.type as leave_type, l.start_date, l.end_date, l.reason, l.status
                        FROM leaves l JOIN users u ON l.user_id = u.id
                        ORDER BY l.start_date DESC LIMIT 30
                    """)
                elif user_role == 'manager':
                    cur.execute("""
                        SELECT u.email as applicant, l.type as leave_type, l.start_date, l.end_date, l.reason, l.status
                        FROM leaves l JOIN users u ON l.user_id = u.id
                        WHERE u.manager_id = %s ORDER BY l.start_date DESC LIMIT 20
                    """, (user_id,))
                else:
                    cur.execute("""
                        SELECT u.email as applicant, l.type as leave_type, l.start_date, l.end_date, l.reason, l.status
                        FROM leaves l JOIN users u ON l.user_id = u.id
                        WHERE l.user_id = %s ORDER BY l.start_date DESC
                    """, (user_id,))
                leaves = cur.fetchall()
                leave_counts = {}
                if leaves:
                    for lv in leaves:
                        leave_counts[lv['status']] = leave_counts.get(lv['status'], 0) + 1
                        lines.append(
                            f"- [{lv['status'].upper()}] {lv['applicant']} applied for {lv['leave_type']} "
                            f"from {lv['start_date']} to {lv['end_date']} | Reason: {lv['reason']}"
                        )
                    for s, c in leave_counts.items():
                        lines.append(f"Total {s} leave requests: {c}")
                else:
                    lines.append("No leave requests on record.")
            except Exception as e:
                lines.append(f"[Leave data error: {e}]")

        conn.close()
    except Exception as e:
        lines.append(f"[Database connection error: {e}]")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    return "\n".join(lines)


# Common greetings that don't need DB data
_GREETING_WORDS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening",
                   "thanks", "thank you", "bye", "goodbye", "ok", "okay", "sure", "great"}

def invoke_query_reply(query_text, history=[], user_id=1, chat_mode='general', user_role='employee', model_choice='llama'):
    _user_context.user_id = user_id

    # Fast greeting shortcut — no need to load all DB data for simple messages
    q_stripped = query_text.strip().lower().rstrip("!.,?")
    if q_stripped in _GREETING_WORDS or len(q_stripped.split()) <= 2 and q_stripped in _GREETING_WORDS:
        return _call_ai(
            [{"role": "user", "content": query_text}],
            f"You are a friendly HR assistant. The user is a {user_role}. Reply warmly and briefly.",
            model_choice=model_choice
        )

    # Fetch live company data from DB based on role
    live_data = _fetch_live_company_data(user_id, user_role)

    # Only use RAG for employees (CEO/manager must only see live DB data to avoid hallucinations)
    rag_context = ""
    if user_role == 'employee':
        docs = _search_knowledge(user_id, query_text)
        if docs:
            rag_context = "\n\n".join(doc["content"] for doc in docs)

    # Build system prompt with live data injected
    system_prompt = (
        f"You are the HR Intelligence Assistant. The user is a {user_role.upper()}.\n\n"
        "RULES:\n"
        "- Use ONLY the live company data below to answer. Do not guess or invent data.\n"
        "- The data has 3 sections: EMPLOYEES, TASKS, and LEAVE REQUESTS.\n"
        "- For questions about leave or who applied for leave, use the LEAVE REQUESTS section.\n"
        "- For questions about employees or headcount, use the EMPLOYEES section.\n"
        "- For questions about tasks or work, use the TASKS section.\n"
        "- If data is not available, say so clearly.\n"
        "- Be concise and professional.\n\n"
        "=== LIVE COMPANY DATA ===\n"
        f"{live_data}\n"
    )

    if rag_context:
        system_prompt += f"\n=== COMPANY POLICIES / DOCUMENTS ===\n{rag_context}\n"

    ai_messages = []
    for h in history:
        role = h.get("role") if isinstance(h, dict) else getattr(h, "role", None)
        content = h.get("content") if isinstance(h, dict) else getattr(h, "content", None)
        if role and content:
            ai_messages.append({"role": role, "content": content})

    ai_messages.append({"role": "user", "content": query_text})

    return _call_ai(ai_messages, system_prompt, model_choice=model_choice)



def _get_embedding(text: str) -> list[float] | None:
    from langchain_ollama import OllamaEmbeddings
    try:
        return OllamaEmbeddings(model="nomic-embed-text", num_gpu=0).embed_query(text)
    except Exception as e:
        print("embed err:", e)
        return None

def _get_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    from langchain_ollama import OllamaEmbeddings
    try:
        return OllamaEmbeddings(model="nomic-embed-text", num_gpu=0).embed_documents(texts)
    except Exception as e:
        print("batch embed err:", e)
        return [None] * len(texts)

class CustomGoogleEmbeddings(Embeddings):
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model="nomic-embed-text", num_gpu=0).embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model="nomic-embed-text", num_gpu=0).embed_query(text)



def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []

    # First try to split by paragraphs
    paragraphs = re.split(r'\n\s*\n', text)

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 1 <= chunk_size:
            current_chunk += ("\n\n" + para if current_chunk else para)
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If a single paragraph is too long, split by sentences
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= chunk_size:
                        current_chunk += (" " + sentence if current_chunk else sentence)
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        # If sentence itself is too long, hard-split
                        if len(sentence) > chunk_size:
                            s_any = cast(Any, sentence)
                            for j in range(0, len(sentence), chunk_size - overlap):
                                chunks.append(s_any[j : j + chunk_size])
                            current_chunk = ""
                        else:
                            current_chunk = sentence
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _extract_text_from_file(file_content: bytes, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()

    if ext in ('.txt', '.md', '.json', '.py', '.js', '.html', '.css', '.log'):
        return file_content.decode('utf-8', errors='replace')
        
    elif ext == '.csv':
        try:
            import pandas as pd
            import io
            df = pd.read_csv(io.BytesIO(file_content))
            return df.to_string(index=False)
        except Exception as e:
            print("csv err", e)
            # Fallback if pandas fails
            return file_content.decode('utf-8', errors='replace')
            
    elif ext in ('.xlsx', '.xls'):
        try:
            import pandas as pd
            import io
            df = pd.read_excel(io.BytesIO(file_content))
            return df.to_string(index=False)
        except Exception as e:
            print("excel err", e)
            return ""

    elif ext == '.pdf':
        try:
            import PyPDF2
            import io
            reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except Exception as e:
            print("pdf err", e)
            return ""

    else:
        # Try as plain text
        try:
            return file_content.decode('utf-8', errors='replace')
        except Exception:
            return ""



def hash_password(password: str) -> str:
    salt = os.environ.get("PASSWORD_SALT", "qa-chat-salt")
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def create_token(user_id: int, email: str, role: str = 'employee') -> str:
    payload = {
        "sub": str(user_id),   # PyJWT v2+ requires sub to be a string
        "email": email,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_H),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    payload = decode_token(token)
    if payload and "sub" in payload:
        payload["sub"] = int(payload["sub"])  # cast back to int for DB queries
    if not payload:
        return None
    return payload  # {"sub": user_id, "email": email, ...}


def require_auth(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                "success": False, 
                "message": "Unauthorized",
                "reply": "Your session has expired. Please log in again."
            }), 401
        return f(user, *args, **kwargs)

    return wrapper



@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email    = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    role     = (data.get("role") or "employee").strip().lower()
    employee_id = (data.get("employee_id") or "").strip()

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"success": False, "message": "Invalid email address"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters"}), 400
    if role not in ["ceo", "manager", "employee"]:
        return jsonify({"success": False, "message": "Invalid role"}), 400

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify({"success": False, "message": "Email already registered"}), 409

            if role in ["ceo", "manager"]:
                cur.execute("SELECT id FROM users WHERE role = %s", (role,))
                if cur.fetchone():
                    return jsonify({
                        "success": False, 
                        "message": f"A user with the role of {role} already exists. Registration of additional {role} accounts is restricted."
                    }), 400

            hashed = hash_password(password)
            try:
                cur.execute(
                    "INSERT INTO users (email, password, role, employee_id) VALUES (%s, %s, %s, %s) RETURNING id, email, role, employee_id, total_leaves, used_leaves",
                    (email, hashed, role, employee_id if employee_id else None),
                )
                user = cur.fetchone()
            except psycopg2.IntegrityError as e:
                if 'employee_id' in str(e):
                    return jsonify({"success": False, "message": "Employee ID already exists"}), 409
                raise e
        conn.commit()

        token = create_token(user["id"], user["email"])
        return jsonify({
            "success": True,
            "token": token,
            "user": {"id": user["id"], "email": user["email"], "role": user["role"], "employee_id": user["employee_id"], "total_leaves": user["total_leaves"], "used_leaves": user["used_leaves"]},
        }), 201

    except Exception as e:
        conn.rollback()
        print("reg err", e)
        return jsonify({"success": False, "message": f"Registration failed: {str(e)}"}), 500
    finally:
        conn.close()


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email    = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, email, password, role, employee_id, total_leaves, used_leaves FROM users WHERE email = %s", (email,))
            user = cur.fetchone()

        if not user or user["password"] != hash_password(password):
            return jsonify({"success": False, "message": "Invalid email or password"}), 401

        token = create_token(user["id"], user["email"], user["role"])
        return jsonify({
            "success": True,
            "token": token,
            "user": {"id": user["id"], "email": user["email"], "role": user["role"], "employee_id": user["employee_id"], "total_leaves": user["total_leaves"], "used_leaves": user["used_leaves"]},
        })

    except Exception as e:
        print("log err", e)
        return jsonify({"success": False, "message": f"Login failed: {str(e)}"}), 500
    finally:
        conn.close()


@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    """
    Self-service password reset.
    Identity proof: email + role (employee / manager / ceo).
    No admin required. Works for all users regardless of employee_id.
    """
    data         = request.get_json() or {}
    email        = (data.get("email") or "").strip().lower()
    role         = (data.get("role") or "").strip().lower()
    new_password = (data.get("new_password") or "").strip()

    if not email or not role or not new_password:
        return jsonify({"success": False, "message": "Email, role, and new password are all required"}), 400

    if role not in ["employee", "manager", "ceo"]:
        return jsonify({"success": False, "message": "Invalid role selected"}), 400

    if len(new_password) < 6:
        return jsonify({"success": False, "message": "New password must be at least 6 characters"}), 400

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Verify the user exists with matching email AND role
            cur.execute(
                "SELECT id, email FROM users WHERE email = %s AND role = %s",
                (email, role)
            )
            user = cur.fetchone()

            if not user:
                return jsonify({"success": False, "message": "No account found matching that email and role. Please check your details."}), 404

            hashed = hash_password(new_password)
            cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, user["id"]))
        conn.commit()
        return jsonify({"success": True, "message": "Password reset successfully! You can now sign in with your new password."})

    except Exception as e:
        conn.rollback()
        print("reset_pw err", e)
        return jsonify({"success": False, "message": f"Reset failed: {str(e)}"}), 500
    finally:
        conn.close()


@app.route("/api/auth/github")
def github_login():
    if not GITHUB_CLIENT_ID:
        return jsonify({"success": False, "message": "GitHub OAuth not configured"}), 503
    state = secrets.token_urlsafe(16)
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&scope=user:email"
        f"&state={state}"
    )
    return redirect(url)


@app.route("/api/auth/github/callback")
def github_callback():
    code  = request.args.get("code")
    error = request.args.get("error")

    if error or not code:
        return redirect(f"{FRONTEND_URL}?error=github_denied")

    # Exchange code for access token
    resp = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_SECRET,
            "code": code,
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    token_data = resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return redirect(f"{FRONTEND_URL}?error=github_token_failed")

    # Fetch GitHub user info
    gh_user = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    ).json()

    # Fetch email (may be private)
    emails = requests.get(
        "https://api.github.com/user/emails",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    ).json()
    primary_email = next(
        (e["email"] for e in emails if isinstance(e, dict) and e.get("primary")),
        gh_user.get("email"),
    )

    github_id    = str(gh_user["id"])
    github_login = gh_user.get("login", "")
    avatar_url   = gh_user.get("avatar_url", "")

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Try by github_id first
            cur.execute("SELECT id, email FROM users WHERE github_id = %s", (github_id,))
            user = cur.fetchone()

            if not user:
                # Try by email (merge account)
                if primary_email:
                    cur.execute("SELECT id, email FROM users WHERE email = %s", (primary_email,))
                    user = cur.fetchone()
                    if user:
                        cur.execute(
                            "UPDATE users SET github_id=%s, github_login=%s, avatar_url=%s WHERE id=%s",
                            (github_id, github_login, avatar_url, user["id"]),
                        )

            if not user:
                cur.execute(
                    """INSERT INTO users (email, github_id, github_login, avatar_url)
                       VALUES (%s, %s, %s, %s) RETURNING id, email""",
                    (primary_email, github_id, github_login, avatar_url),
                )
                user = cur.fetchone()

        conn.commit()

        jwt_token = create_token(user["id"], user["email"] or github_login)
        return redirect(f"{FRONTEND_URL}?token={jwt_token}")

    except Exception as e:
        conn.rollback()
        print("gh err", e)
        return redirect(f"{FRONTEND_URL}?error=server_error")
    finally:
        conn.close()


@app.route("/api/me")
@require_auth
def me(current_user):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, email, github_login, avatar_url, created_at, role, employee_id, manager_id, total_leaves, used_leaves FROM users WHERE id = %s",
                (current_user["sub"],),
            )
            user = cur.fetchone()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        return jsonify({"success": True, "user": dict(user)})
    finally:
        conn.close()



@app.route("/api/sessions", methods=["GET"])
@require_auth
def list_sessions(current_user):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT id, title, use_rag, created_at, updated_at
                   FROM chat_sessions
                   WHERE user_id = %s
                   ORDER BY updated_at DESC""",
                (current_user["sub"],),
            )
            sessions = cur.fetchall()
        return jsonify({"success": True, "sessions": [dict(s) for s in sessions]})
    finally:
        conn.close()


@app.route("/api/sessions", methods=["POST"])
@require_auth
def create_session(current_user):
    data  = request.get_json() or {}
    title = (data.get("title") or "New Chat").strip()[:255]

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO chat_sessions (user_id, title) VALUES (%s, %s) RETURNING id, title, created_at, updated_at",
                (current_user["sub"], title),
            )
            session = cur.fetchone()
        conn.commit()
        return jsonify({"success": True, "session": dict(session)}), 201
    except Exception as e:
        conn.rollback()
        print("sess err", e)
        return jsonify({"success": False, "message": "Failed to create session"}), 500
    finally:
        conn.close()


@app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
@require_auth
def delete_session(current_user, session_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM chat_sessions WHERE id=%s AND user_id=%s",
                (session_id, current_user["sub"]),
            )
            if cur.rowcount == 0:
                conn.rollback()
                return jsonify({"success": False, "message": "Session not found"}), 404
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()



@app.route("/api/sessions/<int:session_id>/messages", methods=["GET"])
@require_auth
def get_messages(current_user, session_id):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Verify ownership
            cur.execute(
                "SELECT id FROM chat_sessions WHERE id=%s AND user_id=%s",
                (session_id, current_user["sub"]),
            )
            if not cur.fetchone():
                return jsonify({"success": False, "message": "Session not found"}), 404

            cur.execute(
                "SELECT id, role, content, created_at FROM messages WHERE session_id=%s ORDER BY created_at ASC",
                (session_id,),
            )
            msgs = cur.fetchall()
        return jsonify({"success": True, "messages": [dict(m) for m in msgs]})
    finally:
        conn.close()



@app.route("/api/knowledge/upload", methods=["POST"])
@require_auth
def upload_document(current_user):
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file provided"}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({"success": False, "message": "No file selected"}), 400

    # Read file content
    file_content = file.read()
    filename = file.filename
    file_size = len(file_content)

    # Extract text
    text = _extract_text_from_file(file_content, filename)
    if not text.strip():
        return jsonify({"success": False, "message": "Could not extract text from file"}), 400

    # Chunk the text
    chunks = _chunk_text(text)
    if not chunks:
        return jsonify({"success": False, "message": "No content to process"}), 400

    conn = get_db()
    try:
        # track db
        if PGVECTOR_AVAILABLE and app.config.get('PGVECTOR_ACTIVE'):
            register_vector(conn)
            
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO knowledge_documents (user_id, filename, file_size, chunk_count, status)
                   VALUES (%s, %s, %s, %s, 'ready') RETURNING id""",
                (current_user["sub"], filename, file_size, 1, ), # Simple status for now
            )
            doc_id = cur.fetchone()["id"]
        conn.commit()

        # append to file
        with open(TEXT_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n\n--- Document: {filename} (Uploaded by {current_user.get('github_login', 'User')}) ---\n\n")
            f.write(text)

        # remove old index
        if os.path.exists(VECTOR_STORE_PATH):
            try:
                import shutil
                if os.path.isdir(VECTOR_STORE_PATH):
                    shutil.rmtree(VECTOR_STORE_PATH)
                else:
                    os.remove(VECTOR_STORE_PATH)
                    if os.path.exists(VECTOR_STORE_PATH + ".pkl"): os.remove(VECTOR_STORE_PATH + ".pkl")
            except Exception as e:
                print("faiss rst err", e)

        return jsonify({
            "success": True,
            "message": f"Successfully trained AI with '{filename}'. It will re-index on your next message.",
            "document": {"id": doc_id, "filename": filename, "status": "ready"}
        }), 201

    except Exception as e:
        conn.rollback()
        print("upload err", e)
        return jsonify({"success": False, "message": f"Failed to process document: {str(e)}"}), 500
    finally:
        conn.close()


@app.route("/api/knowledge/train", methods=["POST"])
@require_auth
def train_knowledge(current_user):
    data = request.get_json() or {}
    text_content = data.get("text")
    url = data.get("url")
    
    if not text_content and not url:
        return jsonify({"success": False, "message": "No content or URL provided"}), 400

    try:
        # If URL provided, fetch content (simulating crawling)
        if url:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                # Basic text extraction from HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                text_content = f"\n\n--- Source: {url} ---\n\n" + soup.get_text(separator='\n')
            else:
                return jsonify({"success": False, "message": f"Failed to fetch URL: {resp.status_code}"}), 400

        # Append to inata_index.txt with clear boundaries
        clean_text = (text_content or "").strip()
        with open(TEXT_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n\n\n--- MANUAL TRAINING [{datetime.now().strftime('%Y-%m-%d %H:%M')}] ---\n\n")
            f.write(f"{clean_text}\n\n")

        # 4. Record training in DB for visibility
        conn = get_db()
        try:
            with conn.cursor() as cur:
                label = f"Manual Training: {url[:30]}..." if url else "Manual Text Training"
                cur.execute(
                    """INSERT INTO knowledge_documents (user_id, filename, file_size, chunk_count, status)
                       VALUES (%s, %s, %s, %s, 'ready')""",
                    (current_user["sub"], label, len(text_content), 1),
                )
            conn.commit()
        except Exception as e:
            print("db train err", e)
        finally:
            conn.close()

        # Delete FAISS store to force re-indexing on next chat
        if os.path.exists(VECTOR_STORE_PATH):
            import shutil
            try:
                if os.path.exists(VECTOR_STORE_PATH):
                    if os.path.isdir(VECTOR_STORE_PATH):
                        shutil.rmtree(VECTOR_STORE_PATH, ignore_errors=True)
                    else:
                        os.remove(VECTOR_STORE_PATH)
                # Also index.pkl if separate
                pkl = VECTOR_STORE_PATH + ".pkl"
                if os.path.exists(pkl): os.remove(pkl)
            except Exception as e:
                print("reset err", e)

        return jsonify({"success": True, "message": "Training data updated. The AI will re-index on the next message."})

    except Exception as e:
        print("tr err", e)
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/knowledge/documents", methods=["GET"])
@require_auth
def list_documents(current_user):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, filename, chunk_count, file_size, created_at, status FROM knowledge_documents ORDER BY created_at DESC"
            )
            docs = cur.fetchall()
        return jsonify({"success": True, "documents": [dict(d) for d in docs]})
    finally:
        conn.close()


@app.route("/api/knowledge/documents/<int:doc_id>", methods=["DELETE"])
@require_auth
def delete_document(current_user, doc_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM knowledge_documents WHERE id=%s",
                (doc_id,),
            )
            if cur.rowcount == 0:
                conn.rollback()
                return jsonify({"success": False, "message": "Document not found"}), 404
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/knowledge/stats", methods=["GET"])
@require_auth
def knowledge_stats(current_user):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT COUNT(*) as doc_count FROM knowledge_documents WHERE status='ready'"
            )
            doc_count = cur.fetchone()["doc_count"]

            chunk_count = 0
            try:
                cur.execute(
                    "SELECT COUNT(*) as chunk_count FROM knowledge_chunks WHERE embedding IS NOT NULL"
                )
                chunk_count = cur.fetchone()["chunk_count"]
            except:
                # Table might not exist without PGVector
                conn.rollback() # Important: rollback failed query to continue connection
                chunk_count = doc_count * 10 # Estimated

        return jsonify({
            "success": True,
            "stats": {
                "document_count": doc_count,
                "chunk_count": chunk_count,
            }
        })
    finally:
        conn.close()


def get_vector_store():
    embeddings = CustomGoogleEmbeddings()
    if os.path.exists(VECTOR_STORE_PATH):
        try:
            print("loading vectors")
            return FAISS.load_local(VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
            print("faiss err", e)
            
    print("making new vectors")
    if not os.path.exists(TEXT_FILE_PATH):
        os.makedirs(os.path.dirname(os.path.abspath(TEXT_FILE_PATH)), exist_ok=True)
        with open(TEXT_FILE_PATH, "w", encoding="utf-8") as f:
            f.write("QAWebPrints Infocorp LLP Consolidated Knowledge Base\n")
            
    with open(TEXT_FILE_PATH, "r", encoding="utf-8") as f:
        text = f.read()
        
    chunks = _chunk_text(text)
    print("split chunks")
    
    docs = [Document(page_content=chunk, metadata={"source": "inata_index.txt"}) for chunk in chunks]
    
    if docs:
        db = FAISS.from_documents(docs, embeddings)
        db.save_local(VECTOR_STORE_PATH)
        print("vectors saved")
        return db
    else:
        db = FAISS.from_texts(["QAWebPrints"], embeddings)
        db.save_local(VECTOR_STORE_PATH)
        print("vectors saved")
        return db

def _search_knowledge(user_id: int, query: str, top_k: int = RAG_TOP_K) -> List[Any]:
    if PGVECTOR_AVAILABLE and app.config.get('PGVECTOR_ACTIVE'):
        query_embedding = _get_embedding(query)
        if query_embedding is None:
            return []

        try:
            conn = get_db()
            register_vector(conn)

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT kc.content, kc.chunk_index, kd.filename,
                              1 - (kc.embedding <=> %s::vector) as similarity
                       FROM knowledge_chunks kc
                       JOIN knowledge_documents kd ON kc.document_id = kd.id
                       WHERE kc.user_id = %s
                         AND kc.embedding IS NOT NULL
                         AND kd.status = 'ready'
                       ORDER BY kc.embedding <=> %s::vector
                       LIMIT %s""",
                    (query_embedding, user_id, query_embedding, top_k),
                )
                results = cur.fetchall()

                # Filter by similarity threshold
                filtered = [
                    dict(r) for r in results
                    if r["similarity"] >= RAG_SIMILARITY_THRESHOLD
                ]
                conn.close()
                return filtered

        except Exception as e:
            print("rag err", e)
            return []
    else:
        # Fallback to local FAISS store search
        try:
            db = get_vector_store()
            results = db.similarity_search_with_score(query, k=top_k)
            filtered = []
            for i, (doc, score) in enumerate(results):
                similarity = 1.0 / (1.0 + score)
                print("doc score:", similarity)
                if similarity >= RAG_SIMILARITY_THRESHOLD:
                    filtered.append({
                        "content": doc.page_content,
                        "filename": doc.metadata.get("source", "idata_index.txt"),
                        "similarity": similarity
                    })
            print("filtered docs:", len(filtered), "/", len(results))
            return filtered
        except Exception as e:
            print("rag err", e)
            return []



def _call_ai(messages: List[dict], system_prompt: str = None, model_choice: str = 'llama') -> str:
    llm = get_llm(model_choice)
    if not llm:
        return "AI model is not available. Please ensure Ollama is running."

    lc_messages = []
    if system_prompt:
        lc_messages.append(SystemMessage(content=system_prompt))
    else:
        lc_messages.append(SystemMessage(content="You are a helpful company assistant for QAWebPrints. Assist employees, managers, and CEOs with company queries, task tracking, and leave requests."))

    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role in ("assistant", "ai"):
            lc_messages.append(AIMessage(content=content))

    try:
        print("calling llm")
        response = llm.invoke(lc_messages)

        # Safely convert list content to plain string
        content = response.content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
                elif isinstance(part, str):
                    text_parts.append(part)
            return " ".join(text_parts).strip()

        return str(content).strip() if content else "I'm sorry, I could not generate a response. Please try again."
    except Exception as e:
        print("llm err", e)
        return "The AI model is taking too long to respond. Please try again in a moment."


@app.route("/api/chat", methods=["POST"])
@require_auth
def chat(current_user):
    """
    Send a message and get an AI reply.
    Body: { "message": str, "session_id": int | null, "use_rag": bool, "chat_mode": str }
    chat_mode: 'general' | 'company' | 'leave'  (defaults to 'general')
    If session_id is null, a new session is automatically created.
    """
    data       = request.get_json() or {}
    message    = (data.get("message") or "").strip()
    session_id = data.get("session_id")
    use_rag    = data.get("use_rag", True)  # RAG enabled by default
    chat_mode  = data.get("chat_mode", "general")  # 'general', 'company', or 'leave'
    model_choice = data.get("model_choice", "llama")

    if not message:
        return jsonify({"success": False, "message": "Message cannot be empty"}), 400

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # session management
            if session_id:
                cur.execute(
                    "SELECT id, use_rag FROM chat_sessions WHERE id=%s AND user_id=%s",
                    (session_id, current_user["sub"]),
                )
                session_row = cur.fetchone()
                if not session_row:
                    return jsonify({"success": False, "message": "Session not found", "reply": "Chat session not found."}), 404
                use_rag = session_row.get("use_rag", True)
            else:
                # Auto-create a session titled after the first ~50 chars
                title = (message[:50] + "...") if len(message) > 50 else message
                cur.execute(
                    "INSERT INTO chat_sessions (user_id, title, use_rag) VALUES (%s, %s, %s) RETURNING id",
                    (current_user["sub"], title, use_rag),
                )
                session_id = cur.fetchone()["id"]

            # get history
            cur.execute(
                """SELECT role, content FROM messages
                   WHERE session_id=%s ORDER BY created_at ASC
                   LIMIT 40""",
                (session_id,),
            )
            history = cur.fetchall()

            # store user msg
            cur.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
                (session_id, "user", message),
            )

            # update time
            cur.execute(
                "UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                (session_id,),
            )

        conn.commit()

        # Set context for tool usage
        _user_context.user_id = current_user["sub"]

        # --- Intelligent Unified Routing ---
        user_role = current_user.get("role", "employee")
        print(f"Handling query | mode={chat_mode} | user_id={current_user['sub']} | role={user_role}")
        reply = invoke_query_reply(
            message,
            history=history,
            user_id=current_user["sub"],
            chat_mode=chat_mode,
            model_choice=model_choice,
            user_role=user_role
        )

        # store ai reply
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
                    (session_id, "assistant", reply),
                )
            conn.commit()
        except Exception as e:
            print("ai save err", e)

        return jsonify({
            "success": True,
            "reply": reply,
            "session_id": session_id,
            "rag_sources": [] 
        })

    except Exception as e:
        conn.rollback()
        print("chat err", e)
        return jsonify({"success": False, "reply": "Server error occurred.", "message": str(e)}), 500
    finally:
        conn.close()



@app.route("/api/sessions/<int:session_id>/rag", methods=["PUT"])
@require_auth
def toggle_rag(current_user, session_id):
    data = request.get_json() or {}
    use_rag = data.get("use_rag", True)

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE chat_sessions SET use_rag=%s WHERE id=%s AND user_id=%s",
                (use_rag, session_id, current_user["sub"]),
            )
            if cur.rowcount == 0:
                conn.rollback()
                return jsonify({"success": False, "message": "Session not found"}), 404
        conn.commit()
        return jsonify({"success": True, "use_rag": use_rag})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()



@app.route("/api/health")
def health():
    try:
        conn = get_db()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False

    # Check if pgvector extension is available
    pgvector_ok = False
    if db_ok:
        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_extension WHERE extname='vector'")
                pgvector_ok = cur.fetchone() is not None
            conn.close()
        except Exception:
            pass

    return jsonify({
        "status": "ok",
        "database": "connected" if db_ok else "disconnected",
        "pgvector": "enabled" if pgvector_ok else "not available",
        "ai": "configured" if GEMINI_API_KEY else "not configured",
    })



from routes_rbac import rbac_bp, init_rbac
init_rbac(get_db, require_auth)
app.register_blueprint(rbac_bp)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
