import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "log_level": record.levelname,
            "service": "shipflow-api",
            "operation": getattr(record, "operation", None),
            "request_id": getattr(record, "request_id", None),
            "user_id": getattr(record, "user_id", None),
            "entity": getattr(record, "entity", None),
            "status": getattr(record, "status", None),
            "error_code": getattr(record, "error_code", None),
            "error_message": getattr(record, "error_message", None),
            "message": record.getMessage(),
        }
        # Remove None values
        return json.dumps({k: v for k, v in log_record.items() if v is not None})

def get_logger(name: str = "shipflow-api") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
