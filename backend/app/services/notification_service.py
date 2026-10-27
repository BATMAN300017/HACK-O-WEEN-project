import sqlite3
from typing import Optional
from app.utils.ids import generate_id
from app.utils.time import utc_now_iso

def send_notification(
    conn: sqlite3.Connection,
    title: str,
    message: str,
    recipient_user_id: Optional[str] = None,
    link: Optional[str] = None
):
    notif_id = generate_id("NTF")
    now = utc_now_iso()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO notifications (id, recipient_user_id, title, message, link, is_read, created_at)
        VALUES (?, ?, ?, ?, ?, 0, ?)
    """, (notif_id, recipient_user_id, title, message, link, now))
