import sqlite3
import json


def get_db_connection():
    conn = sqlite3.connect("rag_app.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_application_logs():
    with get_db_connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS application_logs
                       (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        user_query TEXT,
                        gpt_response TEXT,
                        gpt_response_sources TEXT,
                        model TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
        )
        try:
            conn.execute("SELECT gpt_response_sources FROM application_logs LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute(
                "ALTER TABLE application_logs ADD COLUMN gpt_response_sources TEXT"
            )


def insert_application_logs(
    session_id, user_query, gpt_response, gpt_response_sources, model
):
    with get_db_connection() as conn:
        sources_json = json.dumps(gpt_response_sources if gpt_response_sources else [])
        conn.execute(
            """INSERT INTO application_logs 
                       (session_id, user_query, gpt_response, gpt_response_sources, model) 
                       VALUES (?, ?, ?, ?, ?)""",
            (session_id, user_query, gpt_response, sources_json, model),
        )


def get_chat_history(session_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT user_query, gpt_response, gpt_response_sources 
                          FROM application_logs 
                          WHERE session_id = ? ORDER BY created_at""",
            (session_id,),
        )

        history = []
        rows = cursor.fetchall()
        for row in rows:
            history.append({"role": "user", "content": row["user_query"]})

            llm_sources_list = []
            if row["gpt_response_sources"]:
                try:
                    llm_sources_list = json.loads(row["gpt_response_sources"])
                except json.JSONDecodeError:
                    print(f"Error decoding sources JSON: {row['gpt_response_sources']}")

            history.append(
                {
                    "role": "ai",
                    "content": row["gpt_response"],
                    "sources": llm_sources_list,
                }
            )
        return history
