"""Detection category definitions for mastiff code review."""

from __future__ import annotations

CATEGORY_DEFINITIONS: dict[str, dict[str, str | list[str]]] = {
    "blocking": {
        "name": "Blocking/Deadlock",
        "description": (
            "Synchronous blocking calls in async contexts, potential deadlocks, "
            "and operations that block the event loop or main thread."
        ),
        "examples": [
            "time.sleep() in an async function",
            "Synchronous I/O in an event loop",
            "Acquiring locks in inconsistent order",
            "Blocking HTTP calls in async handlers",
        ],
    },
    "race_condition": {
        "name": "Race Condition",
        "description": (
            "Shared mutable state accessed without proper synchronization, "
            "TOCTOU vulnerabilities, and non-atomic operations on shared resources."
        ),
        "examples": [
            "Global variable modified from multiple threads without locks",
            "Check-then-act patterns on shared state",
            "Non-atomic read-modify-write on shared counters",
            "Concurrent dict/list mutations without synchronization",
        ],
    },
    "degradation": {
        "name": "Degradation",
        "description": (
            "Performance regressions including O(n^2) or worse algorithms, "
            "excessive allocations, missing caches, and unbounded growth."
        ),
        "examples": [
            "Nested loops creating O(n^2) complexity",
            "Loading entire database table into memory",
            "Missing pagination on large result sets",
            "Repeated expensive computations without caching",
        ],
    },
    "resource_leak": {
        "name": "Resource Leak",
        "description": (
            "File handles, database connections, network sockets, or other "
            "resources opened but not properly closed or released."
        ),
        "examples": [
            "open() without context manager or close()",
            "Database connection not returned to pool",
            "Subprocess started without waiting or cleanup",
            "Event listeners registered but never removed",
        ],
    },
}
