import logging
import logging.config
import re
from typing import Any

from sellpilot.core.config import Settings
from sellpilot.core.middleware import request_id_context

SENSITIVE_PATTERN = re.compile(
    r"(?i)(password|passwd|secret|api[_-]?key|apikey|access[_-]?token|"
    r"refresh[_-]?token|token|authorization|cookie|partner[_-]?key|jwt|credential)"
    r"\s*[:=]\s*([^\s,;]+)"
)


def redact_sensitive(value: Any) -> str:
    return SENSITIVE_PATTERN.sub(r"\1=[REDACTED]", str(value))


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_sensitive(record.getMessage())
        record.args = ()
        record.request_id = request_id_context.get() or "-"
        return True


class SensitiveFormatter(logging.Formatter):
    """Preserve tracebacks while applying the same redaction to exception text."""

    def formatException(self, ei: tuple[type[BaseException], BaseException, Any]) -> str:
        return redact_sensitive(super().formatException(ei))


def configure_logging(settings: Settings) -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"sensitive": {"()": SensitiveDataFilter}},
            "formatters": {
                "default": {
                    "()": SensitiveFormatter,
                    "format": (
                        "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
                    ),
                }
            },
            "handlers": {
                "stderr": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["sensitive"],
                    "stream": "ext://sys.stderr",
                }
            },
            "root": {"handlers": ["stderr"], "level": settings.log_level},
        }
    )
