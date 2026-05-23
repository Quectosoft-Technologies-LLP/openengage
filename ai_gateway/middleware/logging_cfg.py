"""
Structured JSON logging for production (ELK/Loki compatible).
"""
import logging, json, sys, os
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp":  datetime.utcnow().isoformat() + "Z",
            "level":      record.levelname,
            "logger":     record.name,
            "message":    record.getMessage(),
            "service":    "openengage-ai-gateway",
            "env":        os.getenv("ENV", "production"),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        return json.dumps(log_entry)

def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO if not os.getenv("DEBUG") else logging.DEBUG)
    # Suppress noisy libs
    for lib in ["uvicorn.access", "httpx", "sqlalchemy.engine"]:
        logging.getLogger(lib).setLevel(logging.WARNING)
    return root_logger
