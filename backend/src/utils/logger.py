"""Structured logging utilities."""
import logging
import json
from datetime import datetime, timezone
from typing import Any


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "extra"):
            log_entry.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    """
    Get configured logger.
    
    Args:
        name: Logger name (e.g., "agent.intake")
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


def create_audit_entry(
    stage: str,
    action: str,
    details: dict[str, Any] = None
) -> dict[str, Any]:
    """
    Create standardized audit log entry.
    
    Args:
        stage: Current workflow stage
        action: Action performed
        details: Additional details
        
    Returns:
        Audit log entry dict
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "action": action,
        "details": details or {}
    }
