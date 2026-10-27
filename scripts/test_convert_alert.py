import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.database import get_db_connection
from app.services.alert_service import convert_alert_to_investigation

with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT id, alert_ref FROM alerts WHERE status != 'CONVERTED_TO_INVESTIGATION' LIMIT 1")
    row = cursor.fetchone()
    if not row:
        cursor.execute("SELECT id, alert_ref FROM alerts LIMIT 1")
        row = cursor.fetchone()
    
    alert_id = row[0]
    print(f"Testing alert conversion on: {alert_id} ({row[1]})")
    res = convert_alert_to_investigation(conn, alert_id, "Sarah Lin (Investigator)")
    print("Conversion result:", res)
