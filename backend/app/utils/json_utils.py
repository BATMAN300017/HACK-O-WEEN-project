import json
from typing import Any, Union

def safe_json_loads(val: Any, default: Any = None) -> Any:
    """Safely parse JSON data, handling already parsed dicts/lists from PostgreSQL JSONB."""
    if val is None:
        return {} if default is None else default
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, (str, bytes, bytearray)):
        try:
            return json.loads(val)
        except Exception:
            return {} if default is None else default
    return {} if default is None else default
