import logging
import logging.config

from app.config import settings


class GunicornFilter(logging.Filter):
    def filter(self, record):
        # workaround to remove the duplicate access log
        try:
            if '"- - HTTP/1.0" 0 0' in record.msg:
                return False
        finally:
            return True


class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    cyan = "\x1b[36m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: cyan,
        logging.INFO: grey,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red
    }

    def formatColor(self, color, message, reset=True, reset_override=None) -> str:
        reset_color = self.reset
        if reset == False and reset_override:
            reset_color = reset_override

        return f"{color}{message}{reset_color}"

    def format(self, record) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(
            fmt=self.formatColor(log_fmt, settings.get("LOG_FORMAT")),
            datefmt=self.formatColor(self.yellow, settings.get(
                "LOG_DATE_FORMAT"), reset=False, reset_override=log_fmt),
            style="{")
        return formatter.format(record)

    def formatException(self, ei) -> str:
        return self.formatColor(self.FORMATS[logging.CRITICAL], super().formatException(ei))

    def formatStack(self, stack_info: str) -> str:
        return self.formatColor(self.FORMATS[logging.CRITICAL], super().formatStack(stack_info))


def setup_logging():
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "gunicorn_filter": {
                "()": GunicornFilter
            }
        },
        "formatters": {
            "standard": {
                "()": CustomFormatter
            }
        },
        "handlers": {
            "console": {
                "formatter": "standard",
                "class": "logging.StreamHandler",
                "filters": ["gunicorn_filter"],
            }
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": settings.get("LOG_LEVEL")
            }
        }
    }

    logging.config.dictConfig(config)
