import os
import sqlite3
import time

# 1. Setup a custom SQLite database to show MCP in action
db_path = "mcp_demo.db"
if os.path.exists(db_path):
    os.remove(db_path)
    
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute('''CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, role TEXT, salary INTEGER)''')
c.executemany("INSERT INTO employees (name, role, salary) VALUES (?, ?, ?)", [
    ("Alice", "Engineering Manager", 120000),
    ("Bob", "Software Developer", 95000),
    ("Charlie", "Designer", 85000),
    ("David", "CEO", 250000)
])
conn.commit()
conn.close()
print("[+] Created sample 'mcp_demo.db' SQLite database")

# 2. Tell the Backend to hook into an SQLite Server on boot
os.environ["MCP_SERVER_CMD"] = "mcp-server-sqlite"
os.environ["MCP_SERVER_ARGS"] = f"--db {db_path}"

import app
# Force using Google Gemini for tools context demonstration
app.GROQ_API_KEY = ""  # Disable Groq so get_llm() falls back to Gemini

# Give the daemon thread a few seconds to boot the MCP server and sync tools
time.sleep(6) 

print("\n--- Bootloader Complete ---")
print("These are the LangChain tools the AI just inherited dynamically via MCP:")
tools = app.mcp_client.get_lc_tools()
for t in tools:
    print(f" - {t.name}: {t.description}")

print("\n------------------------------------------------------------")
query = "Look into the database and tell me who the CEO is and what their salary is."
print(f"USER: {query}")
print("System: Invoking LangChain (This will trigger Groq/Gemini to emit a Tool Call...)")

# We pass this test query into the core logic we just modified
reply = app._call_ai([{"role": "user", "content": query}], "You are a helpful AI assistant with database access. You MUST use the provided SQLite tools (like read_query, list_tables) to answer the user's questions. Do not say you don't have access.")

print(f"\nAI REPLY:\n{reply}")
print("------------------------------------------------------------")
