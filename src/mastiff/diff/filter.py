"""Filter DiffHunks by binary status, exclude patterns, and sensitive paths."""

from __future__ import annotations

from fnmatch import fnmatch

from mastiff.core.models import DiffHunk


def _matches_pattern(file_path: str, pattern: str) -> bool:
    """Check if file_path matches a glob pattern, supporting ** for directories.

    ``**`` is treated as matching zero or more directory components, consistent
    with gitignore-style semantics.
    """
    # Direct fnmatch check
    if fnmatch(file_path, pattern):
        return True

    # Handle ** prefix: strip leading **/ and match against all sub-paths
    # e.g., "**/node_modules/**" → "node_modules/**" should match "node_modules/pkg/index.js"
    stripped = pattern
    while stripped.startswith("**/"):
        stripped = stripped[3:]

    # Try the stripped pattern against full path and sub-paths
    parts = file_path.split("/")
    for i in range(len(parts)):
        partial = "/".join(parts[i:])
        if fnmatch(partial, stripped):
            return True

    # Also match against just the basename
    if fnmatch(parts[-1], pattern):
        return True
    if stripped != pattern and fnmatch(parts[-1], stripped):
        return True

    return False


def filter_hunks(
    hunks: list[DiffHunk],
    *,
    exclude_patterns: list[str] | None = None,
    never_send_paths: list[str] | None = None,
) -> list[DiffHunk]:
    """Filter hunks by removing binary files, excluded patterns, and sensitive paths.

    Binary files are always removed regardless of other filters.

    Args:
        hunks: List of DiffHunk models to filter.
        exclude_patterns: Glob patterns (fnmatch) to exclude.
        never_send_paths: Sensitive path patterns that must never be sent.

    Returns:
        Filtered list of DiffHunk models.
    """
    result: list[DiffHunk] = []
    for hunk in hunks:
        # Always filter binary files
        if hunk.is_binary:
            continue

        # Check exclude patterns
        if exclude_patterns:
            excluded = False
            for pattern in exclude_patterns:
                if _matches_pattern(hunk.file_path, pattern):
                    excluded = True
                    break
            if excluded:
                continue

        # Check never_send_paths
        if never_send_paths:
            sensitive = False
            for pattern in never_send_paths:
                if _matches_pattern(hunk.file_path, pattern):
                    sensitive = True
                    break
            if sensitive:
                continue

        result.append(hunk)

    return result
