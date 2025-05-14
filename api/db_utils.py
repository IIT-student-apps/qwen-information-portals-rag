import sqlite3

def get_db_connection():
    conn = sqlite3.connect("rag_app.db")
    conn.row_factory = sqlite3.Row
    return conn

def create_application_logs():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS application_logs
                       (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        user_query TEXT,
                        gpt_response TEXT,
                        model TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

def insert_application_logs(session_id, user_query, gpt_response, model):
    with get_db_connection() as conn:
        conn.execute('INSERT INTO application_logs (session_id, user_query, gpt_response, model) VALUES (?, ?, ?, ?)',
                   (session_id, user_query, gpt_response, model))

def get_chat_history(session_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_query, gpt_response FROM application_logs WHERE session_id = ? ORDER BY created_at', (session_id,))
        return [{"role": "human" if i%2==0 else "ai", "content": row[0] if i%2==0 else row[1]} 
                for i, row in enumerate(cursor.fetchall())]