"""
Retry and circuit-breaker primitives.

Usage
-----
# Retry a function call:
@celestrak_retry()
def fetch_something(): ...

# Circuit breaker (shared singleton per named service):
cb = get_circuit_breaker("celestrak")
result = cb.call(fetch_something, arg1, arg2)
"""
import time
import threading
from enum import Enum
from typing import Callable, Type

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from utils.logging_config import get_logger

logger = get_logger("resilience")


# ── Circuit Breaker ──────────────────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(RuntimeError):
    pass


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        self.name               = name
        self.failure_threshold  = failure_threshold
        self.recovery_timeout   = recovery_timeout
        self.expected_exception = expected_exception
        self._state             = CircuitState.CLOSED
        self._failures          = 0
        self._last_failure_time = 0.0
        self._lock              = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if (
                self._state == CircuitState.OPEN
                and time.monotonic() - self._last_failure_time > self.recovery_timeout
            ):
                self._state = CircuitState.HALF_OPEN
                logger.info(
                    "Circuit transitioned to HALF_OPEN",
                    extra={"circuit": self.name},
                )
            return self._state

    def call(self, func: Callable, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit '{self.name}' is OPEN — downstream unavailable"
            )
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as exc:
            self._record_failure()
            raise

    def _record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state    = CircuitState.CLOSED
                self._failures = 0
                logger.info("Circuit CLOSED after recovery", extra={"circuit": self.name})

    def _record_failure(self) -> None:
        with self._lock:
            self._failures          += 1
            self._last_failure_time  = time.monotonic()
            if self._failures >= self.failure_threshold:
                prev           = self._state
                self._state    = CircuitState.OPEN
                if prev != CircuitState.OPEN:
                    logger.warning(
                        "Circuit OPENED",
                        extra={"circuit": self.name, "failures": self._failures},
                    )

    def get_status(self) -> dict:
        return {
            "name":     self.name,
            "state":    self.state.value,
            "failures": self._failures,
        }


# ── Singleton registry ────────────────────────────────────────────────────────

_breakers: dict = {}
_breaker_lock = threading.Lock()


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    with _breaker_lock:
        if name not in _breakers:
            _breakers[name] = CircuitBreaker(name=name, **kwargs)
        return _breakers[name]


def all_circuit_breaker_statuses() -> list:
    with _breaker_lock:
        return [cb.get_status() for cb in _breakers.values()]


# ── Retry decorators ─────────────────────────────────────────────────────────

def celestrak_retry():
    """3 attempts, exponential 1-10 s backoff, only on network errors."""
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, OSError)),
        before_sleep=before_sleep_log(logger, 20),
        reraise=True,
    )


def groq_retry():
    """3 attempts, exponential 2-20 s backoff, on any exception."""
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=20),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, 20),
        reraise=True,
    )