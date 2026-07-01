import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.environ.get("DB_HOST", "localhost"),
    database=os.environ.get("DB_NAME", "qachat"),
    user=os.environ.get("DB_USER", "postgres"),
    password=os.environ.get("DB_PASS", "adithyan@1")
)
cur = conn.cursor()
cur.execute("SELECT column_name, column_default FROM information_schema.columns WHERE table_name = 'chat_sessions';")
print("Columns in chat_sessions:")
for row in cur.fetchall():
    print(row)

cur.execute("SELECT use_rag FROM chat_sessions ORDER BY created_at DESC LIMIT 5;")
print("\nuse_rag values for recent sessions:")
for row in cur.fetchall():
    print(row)

conn.close()
