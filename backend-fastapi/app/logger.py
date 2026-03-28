"""
Rich structured logging for Briefed backend.

Sets up:
- Color-coded console output with timestamps, level, module, and message
- Timing helpers for measuring pipeline latency end-to-end
- Per-request context (meeting_id, agent_name) injected via structlog
- All log lines are JSON-safe for Cloud Run / Cloud Logging ingestion

Usage:
    from app.logger import get_logger, log_timing
    log = get_logger(__name__)
    log.info("bot_joined", meeting_id=mid, bot_id=bid)

    with log_timing(log, "gemini_stream", meeting_id=mid):
        async for sentence in answer_question_streaming(...):
            ...
"""
from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from typing import Any

# ── ANSI colours for console ──────────────────────────────────────────────────
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_GREEN  = "\033[92m"
_CYAN   = "\033[96m"
_BLUE   = "\033[94m"
_MAGENTA= "\033[95m"
_WHITE  = "\033[97m"

_LEVEL_COLOURS = {
    "DEBUG":    _DIM + _WHITE,
    "INFO":     _GREEN,
    "WARNING":  _YELLOW,
    "ERROR":    _RED + _BOLD,
    "CRITICAL": _RED + _BOLD,
}

_MODULE_COLOUR = _CYAN
_KEY_COLOUR    = _BLUE
_VAL_COLOUR    = _MAGENTA
_TIME_COLOUR   = _DIM


class _RichFormatter(logging.Formatter):
    """
    Single-line coloured format:
    14:23:01.456  INFO     app.main          webhook_received  meeting_id=abc bot_id=xyz
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = self.formatTime(record, "%H:%M:%S")
        ms = f"{record.msecs:03.0f}"
        level_col = _LEVEL_COLOURS.get(record.levelname, "")
        level_str = f"{level_col}{record.levelname:<8}{_RESET}"

        # Shorten module: app.main → app.main (keep last 2 segments)
        parts = record.name.split(".")
        short_mod = ".".join(parts[-2:]) if len(parts) > 1 else record.name
        mod_str = f"{_MODULE_COLOUR}{short_mod:<22}{_RESET}"

        # The message itself
        msg = record.getMessage()

        # Extra key=value pairs attached via log.info("evt", key=val)
        extras = ""
        skip = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
        for k, v in record.__dict__.items():
            if k not in skip and not k.startswith("_"):
                extras += f"  {_KEY_COLOUR}{k}{_RESET}={_VAL_COLOUR}{v!r}{_RESET}"

        time_str = f"{_TIME_COLOUR}{ts}.{ms}{_RESET}"
        line = f"{time_str}  {level_str}  {mod_str}  {_BOLD}{msg}{_RESET}{extras}"

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


class _BriefedLogger(logging.LoggerAdapter):
    """
    Thin wrapper so you can do:
        log.info("event_name", meeting_id="...", latency_ms=123)
    Extra kwargs become LogRecord extra fields rendered as key=value pairs.
    """

    def process(
        self, msg: str, kwargs: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        extra = kwargs.pop("extra", {})
        # Pull all non-standard kwargs into extra
        for k in list(kwargs.keys()):
            if k not in ("exc_info", "stack_info", "stacklevel"):
                extra[k] = kwargs.pop(k)
        kwargs["extra"] = {**self.extra, **extra}
        return msg, kwargs


def get_logger(name: str, **fixed_fields: Any) -> _BriefedLogger:
    """Return a rich logger for the given module name."""
    return _BriefedLogger(logging.getLogger(name), fixed_fields)


# ── Global setup ──────────────────────────────────────────────────────────────

def setup_logging(level: str = "INFO") -> None:
    """
    Call once at startup (in main.py lifespan).
    Replaces the default uvicorn/fastapi logging with our rich formatter.
    Default level is INFO — use LOG_LEVEL env var to override.
    """
    import os
    effective_level = os.getenv("LOG_LEVEL", level).upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_RichFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, effective_level, logging.INFO))

    # Quieten noisy libraries — these flood Cloud Run logs
    for noisy in (
        "httpx", "httpcore", "uvicorn.access", "grpc",
        "hpack", "hpack.hpack", "hpack.table",
        "urllib3", "urllib3.connectionpool",
        "google.auth", "google.auth.transport",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Keep uvicorn startup messages but not every request line
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


# ── Timing context manager ────────────────────────────────────────────────────

@contextmanager
def log_timing(logger: _BriefedLogger, operation: str, **ctx: Any):
    """
    Context manager that logs start + end of an operation with elapsed ms.

    Usage:
        with log_timing(log, "gemini_stream", meeting_id=mid):
            ...

    Logs:
        ⏱  gemini_stream  START   meeting_id='abc'
        ✅  gemini_stream  1234ms  meeting_id='abc'   (or ❌ on exception)
    """
    t0 = time.perf_counter()
    logger.debug(f"⏱  {operation}  START", **ctx)
    try:
        yield
        elapsed = int((time.perf_counter() - t0) * 1000)
        logger.info(f"✅  {operation}  {elapsed}ms", **ctx)
    except Exception as exc:
        elapsed = int((time.perf_counter() - t0) * 1000)
        logger.error(f"❌  {operation}  {elapsed}ms  {exc!r}", **ctx)
        raise
