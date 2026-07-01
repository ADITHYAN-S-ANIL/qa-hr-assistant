import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "qachat")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "adithyan@1")

def check_docs():
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    cur = conn.cursor()
    cur.execute("SELECT filename, status, created_at FROM knowledge_documents ORDER BY created_at DESC LIMIT 5;")
    rows = cur.fetchall()
    print("--- RECENT DOCUMENTS ---")
    for row in rows:
        print(row)
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_docs()
