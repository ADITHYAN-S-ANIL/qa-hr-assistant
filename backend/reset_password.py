import os
import sys
import hashlib
import psycopg2
from dotenv import load_dotenv

def hash_password(password: str) -> str:
    salt = os.environ.get("PASSWORD_SALT", "qa-chat-salt")
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

def main():
    load_dotenv()
    
    if len(sys.argv) < 3:
        print("Usage: python reset_password.py <email> <new_password>")
        print("Example: python reset_password.py employee@test.com newsecurepassword123")
        sys.exit(1)
        
    email = sys.argv[1].strip().lower()
    new_password = sys.argv[2].strip()
    
    if len(new_password) < 6:
        print("ERROR: Password must be at least 6 characters long.")
        sys.exit(1)
        
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", "5432"))
    DB_NAME = os.environ.get("DB_NAME", "qachat")
    DB_USER = os.environ.get("DB_USER", "postgres")
    DB_PASS = os.environ.get("DB_PASS", "postgres")
    
    hashed = hash_password(new_password)
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASS
        )
        with conn.cursor() as cur:
            # Check if user exists
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if not cur.fetchone():
                print(f"ERROR: User '{email}' not found in the database.")
                conn.close()
                sys.exit(1)
                
            cur.execute("UPDATE users SET password = %s WHERE email = %s", (hashed, email))
            conn.commit()
            print(f"SUCCESS: Password for user '{email}' has been reset successfully.")
        conn.close()
    except Exception as e:
        print(f"ERROR: Failed to connect or update database: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
