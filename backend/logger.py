"""
Structured logging module for REV2.
Provides JSON-formatted logs with request tracing capabilities.
"""

import logging
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON-formatted logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom fields if present in record
        if hasattr(record, "request_id") and record.request_id:
            log_data["request_id"] = record.request_id

        if hasattr(record, "extra_fields") and record.extra_fields:
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StructuredLogger:
    """Wrapper around Python logger with structured logging support."""

    def __init__(self, name: str):
        """Initialize structured logger."""
        self.logger = logging.getLogger(name)
        self.request_id: Optional[str] = None

    def _setup_handlers(self):
        """Setup logging handlers if not already configured."""
        if self.logger.handlers:
            return

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        log_format = os.getenv("LOG_FORMAT", "json").lower()

        self.logger.setLevel(getattr(logging, log_level))

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))

        if log_format == "json":
            formatter = JSONFormatter()
        else:
            # Text format: timestamp - level - message
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def set_request_id(self, request_id: str):
        """Set request ID for tracing."""
        self.request_id = request_id

    def clear_request_id(self):
        """Clear request ID."""
        self.request_id = None

    def _log(
        self,
        level: int,
        message: str,
        exc_info: bool = False,
        extra_fields: Optional[Dict[str, Any]] = None,
    ):
        """Internal logging method with structured fields."""
        self._setup_handlers()

        # Create extra dict for custom fields
        extra_dict = {"extra_fields": extra_fields or {}}
        if self.request_id:
            extra_dict["request_id"] = self.request_id

        self.logger.log(level, message, extra=extra_dict, exc_info=exc_info)

    def debug(self, message: str, **extra_fields):
        """Log debug message."""
        self._log(logging.DEBUG, message, extra_fields=extra_fields)

    def info(self, message: str, **extra_fields):
        """Log info message."""
        self._log(logging.INFO, message, extra_fields=extra_fields)

    def warning(self, message: str, **extra_fields):
        """Log warning message."""
        self._log(logging.WARNING, message, extra_fields=extra_fields)

    def error(self, message: str, exc_info: bool = False, **extra_fields):
        """Log error message."""
        self._log(logging.ERROR, message, exc_info=exc_info, extra_fields=extra_fields)

    def critical(self, message: str, exc_info: bool = False, **extra_fields):
        """Log critical message."""
        self._log(
            logging.CRITICAL, message, exc_info=exc_info, extra_fields=extra_fields
        )


# Global logger instance
def get_logger(name: str = __name__) -> StructuredLogger:
    """Get or create a structured logger instance."""
    return StructuredLogger(name)
