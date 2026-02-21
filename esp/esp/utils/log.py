from __future__ import absolute_import
import json
import logging

from django.conf import settings


class RequireInScript(logging.Filter):
    def filter(self, record):
        return settings.IS_IN_SCRIPT


class RequireNotInScript(logging.Filter):
    def filter(self, record):
        return not settings.IS_IN_SCRIPT


class StructuredFormatter(logging.Formatter):
    """Format log records as JSON for machine-friendly parsing."""

    _RESERVED_KEYS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())

    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "lineno": record.lineno,
            "funcName": record.funcName,
            "process": record.process,
            "thread": record.threadName,
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in self._RESERVED_KEYS and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, sort_keys=True, default=str)
