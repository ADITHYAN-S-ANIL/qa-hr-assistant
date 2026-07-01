import sqlite3
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, request
import logging

app = Flask(__name__)
# Suppress flask output
log = logging.getLogger('werkzeug')
log.disabled = True

DB_FILE = 'leave_management.db'

def init_db():
    """Initialize the SQLite database with a users_leave table."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users_leave (
                user_id INTEGER PRIMARY KEY,
                total_leave INTEGER DEFAULT 30,
                leave_taken INTEGER DEFAULT 0,
                last_reset_year INTEGER
            )
        ''')
        # Insert a default mock user (user_id = 1) if they don't exist
        current_year = datetime.now().year
        conn.execute('''
            INSERT OR IGNORE INTO users_leave (user_id, total_leave, leave_taken, last_reset_year) 
            VALUES (1, 30, 0, ?)
        ''', (current_year,))
        conn.commit()

def automatic_yearly_reset():
    """
    Background job: checks if the year changed and resets leave for ALL users.
    """
    while True:
        try:
            current_year = datetime.now().year
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.execute(
                    "UPDATE users_leave SET total_leave = 30, leave_taken = 0, last_reset_year = ? WHERE last_reset_year < ?",
                    (current_year, current_year)
                )
                if cursor.rowcount > 0:
                    print(f"[{datetime.now()}] Reset leaves for {cursor.rowcount} users for year {current_year}.")
                conn.commit()
        except Exception as e:
            print(f"Yearly reset error: {e}")
        time.sleep(86400)

@app.route("/leave-status")
def leave_status():
    # user_id is passed from the main backend JWT payload.
    # Each authenticated user gets their OWN leave record.
    user_id = request.args.get("user_id", 1, type=int)

    with sqlite3.connect(DB_FILE) as conn:
        current_year = datetime.now().year

        # Auto-create a leave record for this user if they don't have one yet
        conn.execute('''
            INSERT OR IGNORE INTO users_leave (user_id, total_leave, leave_taken, last_reset_year)
            VALUES (?, 30, 0, ?)
        ''', (user_id, current_year))

        # Lazily enforce yearly reset on fetch
        conn.execute(
            "UPDATE users_leave SET total_leave = 30, leave_taken = 0, last_reset_year = ? WHERE user_id = ? AND last_reset_year < ?",
            (current_year, user_id, current_year)
        )
        conn.commit()

        row = conn.execute(
            "SELECT total_leave, leave_taken FROM users_leave WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if not row:
            return jsonify({"error": "User not found"}), 404

        total, taken = row
        return jsonify({
            "user_id": user_id,
            "total_leave": total,
            "leave_taken": taken,
            "remaining_leave": total - taken
        })

if __name__ == "__main__":
    init_db()
    scheduler_thread = threading.Thread(target=automatic_yearly_reset, daemon=True)
    scheduler_thread.start()
    print("Mock Leave API running on port 5001 with per-user leave tracking...")
    app.run(port=5001)
