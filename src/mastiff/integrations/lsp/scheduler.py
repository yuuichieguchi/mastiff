"""Review scheduler with concurrency limiting and LRU caching."""

from __future__ import annotations

import asyncio
import hashlib
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Coroutine

T = TypeVar("T")


class ReviewScheduler:
    """Schedule reviews with semaphore-based concurrency limiting and LRU cache.

    Args:
        max_concurrent: Maximum number of concurrent reviews.
        cache_max: Maximum number of cached results.
    """

    def __init__(self, max_concurrent: int = 2, cache_max: int = 200) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._cache_max = cache_max

    def _cache_key(self, file_path: str, diff_hash: str) -> str:
        return f"{file_path}:{diff_hash}"

    def diff_hash(self, content: str) -> str:
        """Compute a short SHA-256 hash of content for cache keying.

        Args:
            content: Content to hash.

        Returns:
            First 16 hex characters of the SHA-256 hash.
        """
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_cached(self, file_path: str, diff_hash: str) -> Any | None:
        """Retrieve a cached result, updating LRU order.

        Args:
            file_path: File path for the cache key.
            diff_hash: Content hash for the cache key.

        Returns:
            Cached result, or None on cache miss.
        """
        key = self._cache_key(file_path, diff_hash)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def cache_result(self, file_path: str, diff_hash: str, result: Any) -> None:
        """Store a result in the LRU cache, evicting oldest if full.

        Args:
            file_path: File path for the cache key.
            diff_hash: Content hash for the cache key.
            result: Result to cache.
        """
        key = self._cache_key(file_path, diff_hash)
        self._cache[key] = result
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_max:
            self._cache.popitem(last=False)

    async def run(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run a coroutine with semaphore-based concurrency limiting.

        Args:
            coro: Coroutine to execute.

        Returns:
            The coroutine's result.
        """
        async with self._semaphore:
            return await coro
