import logging
import logging.config
import re
from typing import Any

from sellpilot.core.config import Settings

SENSITIVE_PATTERN = re.compile(
    r"(?i)(password|token|authorization|api[_-]?key|jwt)\s*[:=]\s*([^\s,;]+)"
)


def redact_sensitive(value: Any) -> str:
    return SENSITIVE_PATTERN.sub(r"\1=[REDACTED]", str(value))


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_sensitive(record.getMessage())
        record.args = ()
        return True


def configure_logging(settings: Settings) -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"sensitive": {"()": SensitiveDataFilter}},
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
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
