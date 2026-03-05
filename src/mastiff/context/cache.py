"""LRU file cache with mtime invalidation."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class FileCache:
    """LRU cache that stores values keyed by file path with mtime invalidation.

    When a file's mtime changes, the cached entry is automatically invalidated.

    Args:
        max_entries: Maximum number of entries before LRU eviction.
    """

    def __init__(self, max_entries: int = 100) -> None:
        self._max_entries = max_entries
        self._cache: OrderedDict[Path, tuple[float, Any]] = OrderedDict()

    def get(self, path: Path) -> Any | None:
        """Retrieve a cached value if the file has not been modified.

        Args:
            path: File path to look up.

        Returns:
            The cached value, or None if missing or invalidated.
        """
        if path not in self._cache:
            return None

        stored_mtime, value = self._cache[path]
        try:
            current_mtime = path.stat().st_mtime
        except OSError:
            # File was deleted
            del self._cache[path]
            return None

        if current_mtime != stored_mtime:
            del self._cache[path]
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(path)
        return value

    def put(self, path: Path, value: Any) -> None:
        """Store a value in the cache, keyed by file path.

        Records the file's current mtime for later invalidation checks.

        Args:
            path: File path to use as cache key.
            value: Value to cache.
        """
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return

        # Remove if already exists (will be re-added at end)
        if path in self._cache:
            del self._cache[path]

        self._cache[path] = (mtime, value)

        # Evict oldest if over capacity
        while len(self._cache) > self._max_entries:
            self._cache.popitem(last=False)
