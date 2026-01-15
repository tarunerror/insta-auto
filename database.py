import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_path="processed.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                reel_id TEXT NOT NULL,
                dm_sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, reel_id)
            )
        """)
        conn.commit()
        conn.close()

    def is_processed(self, user_id: str, reel_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM processed_users WHERE user_id = ? AND reel_id = ?",
            (user_id, reel_id)
        )
        result = cursor.fetchone() is not None
        conn.close()
        return result

    def mark_processed(self, user_id: str, username: str, reel_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO processed_users (user_id, username, reel_id) VALUES (?, ?, ?)",
            (user_id, username, reel_id)
        )
        conn.commit()
        conn.close()

    def get_stats(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM processed_users")
        total = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM processed_users WHERE DATE(dm_sent_at) = DATE('now')"
        )
        today = cursor.fetchone()[0]
        conn.close()
        return {"total_dms_sent": total, "dms_sent_today": today}
