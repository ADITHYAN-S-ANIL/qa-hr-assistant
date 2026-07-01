"""
Standalone script to initialise the PostgreSQL database.
Run once before starting the server:
    python init_db.py
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "qachat")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")

EMBEDDING_DIM = 768

DDL = f"""
CREATE TABLE IF NOT EXISTS users (
    id           SERIAL PRIMARY KEY,
    email        VARCHAR(255) UNIQUE,
    password     VARCHAR(255),
    github_id    VARCHAR(100) UNIQUE,
    github_login VARCHAR(100),
    avatar_url   TEXT,
    role         VARCHAR(20) DEFAULT 'employee' CHECK (role IN ('ceo', 'manager', 'employee')),
    employee_id  VARCHAR(50) UNIQUE,
    manager_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    total_leaves DOUBLE PRECISION DEFAULT 16,
    used_leaves  DOUBLE PRECISION DEFAULT 0,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      VARCHAR(255) DEFAULT 'New Chat',
    use_rag    BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id         SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role       VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RAG: Knowledge Documents
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename    VARCHAR(500) NOT NULL,
    file_size   INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    status      VARCHAR(20) DEFAULT 'processing',
    error_msg   TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RAG: Knowledge Chunks
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id          SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector({EMBEDDING_DIM}),
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast history lookups
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_user    ON chat_sessions(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chunks_user_id   ON knowledge_chunks (user_id);

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed')),
    date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS company_messages (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiver_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS unique_ceo ON users (role) WHERE role = 'ceo';
CREATE UNIQUE INDEX IF NOT EXISTS unique_manager ON users (role) WHERE role = 'manager';
"""


def main():
    print(f"Connecting to: {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}")
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASS,
        )
        conn.autocommit = True
        
        with conn.cursor() as cur:
            # Try to enable pgvector, but don't fail if it's missing
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                print("SUCCESS: PGVector extension enabled.")
            except Exception as e:
                print(f"WARNING: PGVector extension not found: {e}")
                print("Knowledge base RAG will be disabled until pgvector is installed.")
            
            # Execute DDL (Note: if vector is missing, knowledge_chunks table creation might fail)
            try:
                cur.execute(DDL)
                print("SUCCESS: Database tables initialized.")
            except Exception as e:
                if 'vector' in str(e).lower():
                    # Basic tables DDL (without PGVector)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, email VARCHAR(255) UNIQUE, password VARCHAR(255), github_id VARCHAR(100) UNIQUE, github_login VARCHAR(100), avatar_url TEXT, role VARCHAR(20) DEFAULT 'employee' CHECK (role IN ('ceo', 'manager', 'employee')), employee_id VARCHAR(50) UNIQUE, manager_id INTEGER REFERENCES users(id) ON DELETE SET NULL, total_leaves DOUBLE PRECISION DEFAULT 16, used_leaves DOUBLE PRECISION DEFAULT 0, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW());
                        CREATE TABLE IF NOT EXISTS chat_sessions (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, title VARCHAR(255) DEFAULT 'New Chat', use_rag BOOLEAN DEFAULT TRUE, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW());
                        CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE, role VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')), content TEXT NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW());
                        CREATE TABLE IF NOT EXISTS knowledge_documents (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, filename VARCHAR(500) NOT NULL, file_size INTEGER DEFAULT 0, chunk_count INTEGER DEFAULT 0, status VARCHAR(20) DEFAULT 'ready', error_msg TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW());
                        CREATE TABLE IF NOT EXISTS tasks (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, description TEXT NOT NULL, status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed')), date DATE DEFAULT CURRENT_DATE, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW());
                        CREATE TABLE IF NOT EXISTS leaves (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, start_date DATE NOT NULL, end_date DATE NOT NULL, start_time VARCHAR(10), end_time VARCHAR(10), status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled', 'declined')), type VARCHAR(20) DEFAULT 'regular' CHECK (type IN ('regular', 'comp-off', 'half-day')), reason TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW());
                        CREATE TABLE IF NOT EXISTS company_messages (id SERIAL PRIMARY KEY, sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, receiver_id INTEGER REFERENCES users(id) ON DELETE CASCADE, content TEXT NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW());
                        CREATE UNIQUE INDEX IF NOT EXISTS unique_ceo ON users (role) WHERE role = 'ceo';
                        CREATE UNIQUE INDEX IF NOT EXISTS unique_manager ON users (role) WHERE role = 'manager';
                    """)
                    print("SUCCESS: Essential tables ready.")
                else:
                    raise e
                    
        conn.close()
    except psycopg2.OperationalError as e:
        print(f"ERROR: Cannot connect to database: {e}")
        print("Make sure PostgreSQL is running and DB_* vars are correct in .env")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
