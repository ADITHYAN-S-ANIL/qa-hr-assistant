import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "qachat")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")

def main():
    print(f"Connecting to: {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}")
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASS,
        )
        conn.autocommit = True
        
        with conn.cursor() as cur:
            # 1. Update existing `users` table
            try:
                print("Updating 'users' table...")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'employee' CHECK (role IN ('ceo', 'manager', 'employee'));")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS employee_id VARCHAR(50) UNIQUE;")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS manager_id INTEGER REFERENCES users(id) ON DELETE SET NULL;")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS total_leaves DOUBLE PRECISION DEFAULT 16;")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS used_leaves DOUBLE PRECISION DEFAULT 0;")
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_ceo ON users (role) WHERE role = 'ceo';")
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_manager ON users (role) WHERE role = 'manager';")
                print("Successfully updated 'users' table.")
            except Exception as e:
                print(f"Error updating 'users' table: {e}")

            # 2. Create `tasks` table
            try:
                print("Creating 'tasks' table...")
                cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    description TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed')),
                    date DATE DEFAULT CURRENT_DATE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """)
                print("Successfully created 'tasks' table.")
            except Exception as e:
                print(f"Error creating 'tasks' table: {e}")

            # 3. Create `leaves` table
            try:
                print("Creating 'leaves' table...")
                cur.execute("""
                CREATE TABLE IF NOT EXISTS leaves (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    start_time VARCHAR(10),
                    end_time VARCHAR(10),
                    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled', 'declined')),
                    type VARCHAR(20) DEFAULT 'regular' CHECK (type IN ('regular', 'comp-off', 'half-day')),
                    reason TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """)
                print("Successfully created 'leaves' table.")
            except Exception as e:
                print(f"Error creating 'leaves' table: {e}")

            # 4. Create `company_messages` table
            try:
                print("Creating 'company_messages' table...")
                cur.execute("""
                CREATE TABLE IF NOT EXISTS company_messages (
                    id SERIAL PRIMARY KEY,
                    sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    receiver_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """)
                print("Successfully created 'company_messages' table.")
            except Exception as e:
                print(f"Error creating 'company_messages' table: {e}")

        conn.close()
        print("Migration complete!")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    main()
