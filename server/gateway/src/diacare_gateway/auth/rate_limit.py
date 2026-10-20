"""In-process limit on failed logins. Enough for one gateway process (no Redis, ADR 0005)."""

import threading
import time
from collections import deque
from collections.abc import Callable


class LoginRateLimiter:
    """Block a key (lower-case e-mail plus client address) after too many recent failures."""

    def __init__(
        self,
        max_failures: int = 5,
        window_seconds: float = 15 * 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max = max_failures
        self._window = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str) -> deque[float]:
        failures = self._failures.setdefault(key, deque())
        cutoff = self._clock() - self._window
        while failures and failures[0] <= cutoff:
            failures.popleft()
        return failures

    def blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._recent(key)) >= self._max

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._recent(key).append(self._clock())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
