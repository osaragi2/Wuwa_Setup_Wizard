import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable

import bpy


# ========== CONSTANTS ==========

UI_CACHE_TTL = 5.0
UI_CACHE_MAX_SIZE = 100
UI_CACHE_METRICS_ENABLED = False


# ========== CACHE ENTRY ==========

# Represents a single cache entry with metadata
@dataclass
class CacheEntry:
    value: Any
    timestamp: float
    access_count: int = 0


# ========== UI CACHE ==========

# Caches UI state to improve panel redraw performance
class UICache:
    _cache: OrderedDict[str, CacheEntry] = OrderedDict()
    _last_active_obj_name: str | None = None
    _last_active_obj_id: int | None = None
    _last_mode: str | None = None
    _last_update_time: float = 0
    _invalidation_tags: dict[str, set[str]] = {}

    _hits: int = 0
    _misses: int = 0

    # ========== CONTEXT DETECTION ==========

    # Checks if context has changed and invalidates cache if needed
    @classmethod
    def _check_context_changed(cls, active_obj: bpy.types.Object | None) -> bool:
        current_time = time.monotonic()
        current_obj_name = active_obj.name if active_obj else None
        current_obj_id = id(active_obj) if active_obj else None
        current_mode = active_obj.mode if active_obj else None

        obj_changed = (
            current_obj_name != cls._last_active_obj_name or
            current_obj_id != cls._last_active_obj_id or
            current_mode != cls._last_mode
        )
        time_expired = (current_time - cls._last_update_time) > UI_CACHE_TTL

        if obj_changed or time_expired:
            cls._cache.clear()
            cls._invalidation_tags.clear()
            cls._last_active_obj_name = current_obj_name
            cls._last_active_obj_id = current_obj_id
            cls._last_mode = current_mode
            cls._last_update_time = current_time
            return True
        return False

    # ========== CACHE OPERATIONS ==========

    # Evicts oldest entries when cache exceeds max size (LRU)
    @classmethod
    def _evict_oldest(cls) -> None:
        while len(cls._cache) >= UI_CACHE_MAX_SIZE:
            cls._cache.popitem(last=False)

    # Gets cached value or computes if cache miss
    @classmethod
    def get(cls, key: str, compute_fn: Callable[[], Any],
            active_obj: bpy.types.Object | None = None,
            tags: set[str] | None = None) -> Any:
        cls._check_context_changed(active_obj)

        if key in cls._cache:
            entry = cls._cache[key]
            entry.access_count += 1
            cls._cache.move_to_end(key)
            cls._hits += 1
            return entry.value

        cls._misses += 1
        cls._evict_oldest()

        value = compute_fn()
        cls._cache[key] = CacheEntry(
            value=value,
            timestamp=time.monotonic()
        )

        if tags:
            for tag in tags:
                if tag not in cls._invalidation_tags:
                    cls._invalidation_tags[tag] = set()
                cls._invalidation_tags[tag].add(key)

        return value

    # ========== INVALIDATION ==========

    # Invalidates all cache entries with given tag
    @classmethod
    def invalidate_by_tag(cls, tag: str) -> int:
        if tag not in cls._invalidation_tags:
            return 0

        keys_to_remove = cls._invalidation_tags[tag]
        count = 0
        for key in list(keys_to_remove):
            if key in cls._cache:
                del cls._cache[key]
                count += 1

        del cls._invalidation_tags[tag]
        return count

    # Invalidates cache entries matching pattern
    @classmethod
    def invalidate_by_pattern(cls, pattern: str) -> int:
        keys_to_remove = [k for k in cls._cache if pattern in k]
        for key in keys_to_remove:
            del cls._cache[key]
        return len(keys_to_remove)

    # Manually clears all cached values
    @classmethod
    def clear(cls) -> None:
        cls._cache.clear()
        cls._invalidation_tags.clear()

    # ========== METRICS ==========

    # Returns cache performance metrics
    @classmethod
    def get_metrics(cls) -> dict[str, Any]:
        total = cls._hits + cls._misses
        hit_rate = (cls._hits / total * 100) if total > 0 else 0
        return {
            "hits": cls._hits,
            "misses": cls._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "size": len(cls._cache),
            "max_size": UI_CACHE_MAX_SIZE
        }

    # Resets cache metrics counters
    @classmethod
    def reset_metrics(cls) -> None:
        cls._hits = 0
        cls._misses = 0
