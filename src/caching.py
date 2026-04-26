"""缓存管理模块 - Ponder Knowledge Platform"""

import time
import json
import hashlib
import threading
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field
from collections import OrderedDict


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    ttl: float = 0  # 0 = no expiry
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return time.time() - self.created_at > self.ttl

    def to_dict(self) -> Dict:
        return {
            "key": self.key, "ttl": self.ttl,
            "created_at": self.created_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "expired": self.is_expired()
        }


class LRUCache:
    """LRU缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: float = 0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            entry.access_count += 1
            entry.last_accessed = time.time()
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.value

    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            self._cache[key] = CacheEntry(
                key=key, value=value,
                ttl=ttl if ttl is not None else self.default_ttl
            )

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._cache.pop(key, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def cleanup_expired(self) -> int:
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            for k in expired_keys:
                del self._cache[k]
            return len(expired_keys)

    def get_or_compute(self, key: str, compute_func: Callable[[], Any],
                       ttl: Optional[float] = None) -> Any:
        value = self.get(key)
        if value is not None:
            return value
        value = compute_func()
        self.put(key, value, ttl)
        return value

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def get_statistics(self) -> Dict:
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 4),
            "entries": [v.to_dict() for v in list(self._cache.values())[:10]]
        }

    def keys(self) -> list:
        return list(self._cache.keys())


class CacheManager:
    """多级缓存管理器"""

    def __init__(self):
        self._caches: Dict[str, LRUCache] = {}

    def create_cache(self, name: str, max_size: int = 1000,
                     default_ttl: float = 0) -> LRUCache:
        cache = LRUCache(max_size=max_size, default_ttl=default_ttl)
        self._caches[name] = cache
        return cache

    def get_cache(self, name: str) -> Optional[LRUCache]:
        return self._caches.get(name)

    def delete_cache(self, name: str) -> bool:
        return self._caches.pop(name, None) is not None

    def clear_all(self) -> None:
        for cache in self._caches.values():
            cache.clear()

    def cleanup_all(self) -> Dict[str, int]:
        results = {}
        for name, cache in self._caches.items():
            results[name] = cache.cleanup_expired()
        return results

    def get_global_statistics(self) -> Dict:
        return {
            name: cache.get_statistics()
            for name, cache in self._caches.items()
        }

    @staticmethod
    def make_key(*args, **kwargs) -> str:
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()


# 全局缓存管理器实例
cache_manager = CacheManager()


def cached(cache_name: str = "default", ttl: Optional[float] = None,
           key_func: Optional[Callable] = None):
    """缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        cache = cache_manager.get_cache(cache_name)
        if cache is None:
            cache = cache_manager.create_cache(cache_name)

        def wrapper(*args, **kwargs):
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{CacheManager.make_key(*args, **kwargs)}"
            result = cache.get(cache_key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.put(cache_key, result, ttl)
            return result

        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_stats = lambda: cache.get_statistics()
        return wrapper
    return decorator
