"""In-memory response cache with TTL + version-based invalidation.

Ecosystem chat answers depend on the playbook catalogue. Two facts let us
cache aggressively:

  1. The catalogue changes only when somebody writes a playbook (commit / adapt
     / adapt-stream). Every other call is a read.
  2. Within one catalogue version, the same query yields the same response —
     deterministic enough for a demo (and the cache enforces consistency for
     judges hitting the same question twice).

Strategy: every cache entry is tagged with the catalogue version at write
time. A write to Firestore bumps the version, which makes every existing
entry unreachable on the next read — no per-entry purge needed. A TTL is
layered on as a safety net (10 min default) so a forgotten version bump
doesn't serve stale data forever.

Storage is process-local — on Cloud Run that means each instance warms its
own cache independently. Acceptable for hackathon-scale traffic; the upgrade
path is Redis or Memorystore when the request volume warrants it.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any


class TTLCache:
    """LRU + TTL + version cache. Thread-safe."""

    def __init__(self, max_size: int = 256, ttl_seconds: float = 600.0) -> None:
        self._store: OrderedDict[str, tuple[float, int, Any]] = OrderedDict()
        self._version = 0
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @property
    def version(self) -> int:
        return self._version

    def invalidate(self) -> None:
        """Bump the version — every cached entry becomes unreachable."""
        with self._lock:
            self._version += 1

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            ts, ver, value = entry
            if ver != self._version or now - ts > self._ttl:
                # Stale by version or expired by TTL — evict.
                self._store.pop(key, None)
                self._misses += 1
                return None
            self._store.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        now = time.time()
        with self._lock:
            self._store[key] = (now, self._version, value)
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "size": len(self._store),
                "version": self._version,
                "hits": self._hits,
                "misses": self._misses,
            }


def normalize_query(query: str) -> str:
    """Cache-key normalization for a natural-language query.

    Lowercase + collapse whitespace. Order/case-insensitive for demo queries
    like "Show me Climate Tech events" vs "show me climate tech events".
    """
    return " ".join(query.lower().split())
