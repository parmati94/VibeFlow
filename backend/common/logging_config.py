"""Logging configuration — colored console (colorlog) + daily rotating file.

A single `setup_logging()` configures the root logger with colored levels for the console
plus a daily-rotating file handler; `get_logger()` returns named loggers. The module-level
`logger` is configured on import so `from backend.common.logging_config import logger`
works everywhere.
"""

import datetime
import logging
import os
from logging.handlers import TimedRotatingFileHandler

import colorlog

# logs live next to this module: backend/common/logs/
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

_CONSOLE_FORMAT = "%(log_color)s%(levelname)-8s%(reset)s %(asctime)s %(filename)s: %(message)s"
_FILE_FORMAT = "%(asctime)s [%(levelname)s] %(filename)s: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"
_LOG_COLORS = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red,bg_white",
}
# Chatty third-party loggers pinned to WARNING so our own logs stay readable.
_NOISY = ("httpx", "httpcore", "urllib3", "spotipy", "apscheduler")


class _DailyRotatingFileHandler(TimedRotatingFileHandler):
    """Roll at midnight, naming each file logfile_YYYY-MM-DD.log."""

    def doRollover(self):
        self.baseFilename = os.path.join(
            _LOG_DIR, f"logfile_{datetime.datetime.now():%Y-%m-%d}.log"
        )
        super().doRollover()


def _coerce_level(level: str | int | None) -> int:
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
    if isinstance(level, int):
        return level
    numeric = getattr(logging, level, None)
    if not isinstance(numeric, int):
        raise ValueError(f"Invalid log level: {level}")
    return numeric


def setup_logging(level: str | int | None = None) -> logging.Logger:
    """Configure the root logger: colored console + daily rotating file. Idempotent —
    existing handlers are cleared first, so it is safe to call more than once."""
    numeric_level = _coerce_level(level)

    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    console = colorlog.StreamHandler()
    console.setFormatter(
        colorlog.ColoredFormatter(
            _CONSOLE_FORMAT, datefmt=_DATEFMT, reset=True, log_colors=_LOG_COLORS
        )
    )

    os.makedirs(_LOG_DIR, exist_ok=True)
    file_handler = _DailyRotatingFileHandler(
        os.path.join(_LOG_DIR, f"logfile_{datetime.datetime.now():%Y-%m-%d}.log"),
        when="midnight",
        interval=1,
        backupCount=7,
    )
    file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_DATEFMT))

    for handler in (console, file_handler):
        handler.setLevel(numeric_level)
        root.addHandler(handler)
    root.setLevel(numeric_level)

    for noisy in _NOISY:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root.info("Logging configured at %s", logging.getLevelName(numeric_level))
    return root


def get_logger(name: str) -> logging.Logger:
    """A named logger. All loggers propagate to the root handlers from setup_logging()."""
    return logging.getLogger(name)


# Configure on import and export a default logger.
setup_logging()
logger = logging.getLogger()
