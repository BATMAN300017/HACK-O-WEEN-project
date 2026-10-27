import logging
import json
import sys
from datetime import datetime, timezone

SENSITIVE_KEYS = {"password", "token", "secret", "authorization", "ssn", "card_number", "cvv"}

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "props"):
            props = getattr(record, "props")
            if isinstance(props, dict):
                redacted = {}
                for k, v in props.items():
                    if any(s in k.lower() for s in SENSITIVE_KEYS):
                        redacted[k] = "[REDACTED]"
                    else:
                        redacted[k] = v
                log_data["details"] = redacted
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [handler]

logger = logging.getLogger("sentinelflow")
