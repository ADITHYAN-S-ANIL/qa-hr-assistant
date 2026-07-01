import os
import psycopg2

def run():
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "5432")
    DB_NAME = os.environ.get("DB_NAME", "qachat")
    DB_USER = os.environ.get("DB_USER", "postgres")
    DB_PASS = os.environ.get("DB_PASS", "adithyan@1")

    print(f"Connecting to: {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute('ALTER TABLE leaves ADD COLUMN IF NOT EXISTS start_time VARCHAR(10);')
            cur.execute('ALTER TABLE leaves ADD COLUMN IF NOT EXISTS end_time VARCHAR(10);')
            print("DB Altered!")
    finally:
        conn.close()

if __name__ == '__main__':
    run()
