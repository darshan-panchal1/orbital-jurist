"""
Structured JSON logging with per-request context propagation.
Import get_logger() everywhere instead of logging.getLogger() directly.
"""
import logging
import sys
import uuid
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger

from config import settings

# ── Context variables (propagated through async tasks automatically) ─────────
_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_trace_id:   ContextVar[str] = ContextVar("trace_id",   default="-")
_case_id:    ContextVar[str] = ContextVar("case_id",    default="-")

_handler_installed = False


def _install_root_handler() -> None:
    global _handler_installed
    if _handler_installed:
        return
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_JSON:
        fmt = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
            rename_fields={"levelname": "level", "asctime": "ts", "name": "logger"},
        )
    else:
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
        )
    handler.setFormatter(fmt)
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Silence chatty third-party libraries
    for noisy in ("httpx", "httpcore", "groq", "chromadb", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _handler_installed = True


class _ContextFilter(logging.Filter):
    """Injects request/trace/case IDs into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get("-")
        record.trace_id   = _trace_id.get("-")
        record.case_id    = _case_id.get("-")
        return True


def get_logger(name: str) -> logging.Logger:
    _install_root_handler()
    logger = logging.getLogger(name)
    # Attach context filter once
    if not any(isinstance(f, _ContextFilter) for f in logger.filters):
        logger.addFilter(_ContextFilter())
    return logger


# ── Context helpers ──────────────────────────────────────────────────────────

def new_request_id() -> str:
    rid = uuid.uuid4().hex[:12]
    _request_id.set(rid)
    return rid


def set_context(*, request_id: str = None, trace_id: str = None, case_id: str = None) -> None:
    if request_id is not None:
        _request_id.set(request_id)
    if trace_id is not None:
        _trace_id.set(trace_id)
    if case_id is not None:
        _case_id.set(case_id)


def get_request_id() -> str:
    return _request_id.get("-")