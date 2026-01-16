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
                comment_id TEXT,
                comment_replied INTEGER DEFAULT 0,
                dm_sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, reel_id)
            )
        """)
        # Add comment_replied column if it doesn't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE processed_users ADD COLUMN comment_id TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            cursor.execute(
                "ALTER TABLE processed_users ADD COLUMN comment_replied INTEGER DEFAULT 0"
            )
        except sqlite3.OperationalError:
            pass  # Column already exists
        conn.commit()
        conn.close()

    def is_processed(self, user_id: str, reel_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM processed_users WHERE user_id = ? AND reel_id = ?",
            (user_id, reel_id),
        )
        result = cursor.fetchone() is not None
        conn.close()
        return result

    def mark_processed(
        self, user_id: str, username: str, reel_id: str, comment_id: str = None
    ):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO processed_users (user_id, username, reel_id, comment_id) VALUES (?, ?, ?, ?)",
            (user_id, username, reel_id, comment_id),
        )
        conn.commit()
        conn.close()

    def mark_comment_replied(self, user_id: str, reel_id: str):
        """Mark that we've replied to this user's comment on this reel"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE processed_users SET comment_replied = 1 WHERE user_id = ? AND reel_id = ?",
            (user_id, reel_id),
        )
        conn.commit()
        conn.close()

    def is_comment_replied(self, user_id: str, reel_id: str) -> bool:
        """Check if we've already replied to this user's comment on this reel"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT comment_replied FROM processed_users WHERE user_id = ? AND reel_id = ?",
            (user_id, reel_id),
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None and result[0] == 1

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
