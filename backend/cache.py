"""
Cache TTL đơn giản trong bộ nhớ (in-memory).
Mục đích: giảm số lần gọi API-Football để không vượt giới hạn free 100 req/ngày.
Phase sau có thể thay bằng Redis mà không đổi interface.
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
            self._store.pop(key, None)  # hết hạn -> xoá
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        # ttl riêng cho từng entry (vd live 30s, standings 6h). Không truyền -> dùng ttl mặc định.
        effective = self.ttl if ttl is None else ttl
        self._store[key] = (time.time() + effective, value)
