import psycopg2, os
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'qachat')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASS = os.environ.get('DB_PASS', 'adithyan@1')

conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
cur = conn.cursor()

# Get two users
cur.execute("SELECT id FROM users LIMIT 2;")
users = cur.fetchall()
if len(users) >= 2:
    cur.execute("INSERT INTO tasks (user_id, date, description, status) VALUES (%s, CURRENT_DATE, 'Working on jira ticket 999 (Frontend)', 'pending');", (users[0][0],))
    cur.execute("INSERT INTO tasks (user_id, date, description, status) VALUES (%s, CURRENT_DATE, 'Working on jira ticket 999 (Backend)', 'completed');", (users[1][0],))
    conn.commit()

cur.execute("SELECT * FROM tasks WHERE description ILIKE '%999%';")
print(cur.fetchall())
conn.close()
