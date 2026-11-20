import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class TTLCache:
    """Small thread-safe in-process cache. Every entry expires after `ttl` seconds."""

    def __init__(self, ttl: float, max_entries: int = 256, clock: Callable[[], float] = time.monotonic):
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.ttl = ttl
        self.max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get_or_set(self, key: str, compute: Callable[[], T]) -> T:
        now = self._clock()
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry[0] > now:
                self.hits += 1
                self._entries.move_to_end(key)
                return entry[1]
            self.misses += 1
        value = compute()
        with self._lock:
            self._entries[key] = (self._clock() + self.ttl, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
        return value

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
