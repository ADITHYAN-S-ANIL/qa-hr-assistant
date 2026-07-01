import app
conn = app.get_db()
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='leaves' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
print("Leaves table columns:", cols)
cur.execute("SELECT * FROM leaves LIMIT 2")
rows = cur.fetchall()
print("Sample rows:", rows)
conn.close()
