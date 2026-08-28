import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'classspace.db')
SCHEMA_PATH = os.path.join(BASE_DIR, 'database', 'schema.sql')

def get_db(db_path=DB_PATH):
    """
    Get a database connection with row factory enabled and foreign keys enforced.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path=DB_PATH, schema_path=SCHEMA_PATH):
    """
    Initialize the database using the schema.sql DDL script.
    """
    conn = get_db(db_path)
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
    print(f"Database initialized successfully at: {db_path}")

def ensure_db_initialized(db_path=DB_PATH):
    """
    Safely and idempotently ensure tables exist without wiping data.
    """
    init_db(db_path=db_path)

if __name__ == '__main__':
    init_db()

