"""
Simple in-memory TTL cache.
Purpose: reduce API-Football calls to stay within the free limit of 100 requests/day.
Can be replaced with Redis later without changing the interface.
"""
import time
from typing import Any, Optional


class TTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if time.time() > expires_at:
            self._store.pop(key, None)  # expired -> delete
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        # per-entry ttl (e.g. live 30s, standings 6h). If not given -> use the default ttl.
        effective = self.ttl if ttl is None else ttl
        self._store[key] = (time.time() + effective, value)
