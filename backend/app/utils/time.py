from datetime import datetime, timezone, timedelta
from typing import Optional

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def utc_now_iso() -> str:
    return utc_now().isoformat()

def parse_iso(ts_str: str) -> datetime:
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

def minutes_ago(minutes: int) -> datetime:
    return utc_now() - timedelta(minutes=minutes)

def minutes_ago_iso(minutes: int) -> str:
    return minutes_ago(minutes).isoformat()
