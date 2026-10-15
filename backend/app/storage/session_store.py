"""
SQLite 会话存储：管理多轮对话的会话和消息。
"""
import sqlite3
from datetime import datetime


class SessionStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        conn.commit()
        conn.close()

    def create_session(self, title: str = "新对话") -> str:
        import uuid
        sid = uuid.uuid4().hex[:12]
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO sessions (session_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (sid, title, now, now),
        )
        conn.commit()
        conn.close()
        return sid

    def list_sessions(self) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_messages(self, session_id: str) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT role, text FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_message(self, session_id: str, role: str, text: str):
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO messages (session_id, role, text, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, text, now),
        )
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
            (now, session_id),
        )
        conn.commit()
        conn.close()

    def delete_session(self, session_id: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

    def rename_session(self, session_id: str, title: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE sessions SET title = ? WHERE session_id = ?",
            (title, session_id),
        )
        conn.commit()
        conn.close()
