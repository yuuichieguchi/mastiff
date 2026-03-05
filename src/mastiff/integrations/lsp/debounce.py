"""Debounce utility for LSP file-save events."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class Debouncer:
    """Debounce async callbacks by key.

    Args:
        delay_ms: Debounce delay in milliseconds.
    """

    def __init__(self, delay_ms: int = 500) -> None:
        self.delay = delay_ms / 1000.0
        self._timers: dict[str, asyncio.Task[None]] = {}

    async def _run_after_delay(self, key: str, callback: Callable[..., Any], *args: Any) -> None:
        await asyncio.sleep(self.delay)
        del self._timers[key]
        await callback(*args)

    def debounce(self, key: str, callback: Callable[..., Any], *args: Any) -> None:
        """Schedule a debounced callback, cancelling any pending one for the same key.

        Args:
            key: Unique key for this debounce group.
            callback: Async callable to invoke after delay.
            *args: Arguments to pass to the callback.
        """
        if key in self._timers:
            self._timers[key].cancel()
        loop = asyncio.get_event_loop()
        self._timers[key] = loop.create_task(self._run_after_delay(key, callback, *args))

    def cancel(self, key: str) -> None:
        """Cancel a pending debounced callback.

        Args:
            key: Key of the debounce group to cancel.
        """
        if key in self._timers:
            self._timers[key].cancel()
            del self._timers[key]
