"""Unified diff parser that produces DiffHunk models."""

from __future__ import annotations

import re

from mastiff.core.models import DiffHunk

_DIFF_HEADER_RE = re.compile(r"^diff --git a/(.*?) b/(.*?)$", re.MULTILINE)
_HUNK_HEADER_RE = re.compile(r"^@@\s+-(\d+)(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s+@@", re.MULTILINE)
_RENAME_FROM_RE = re.compile(r"^rename from (.+)$", re.MULTILINE)
_RENAME_TO_RE = re.compile(r"^rename to (.+)$", re.MULTILINE)
_BINARY_RE = re.compile(r"^Binary files", re.MULTILINE)


def parse_diff(diff_text: str) -> list[DiffHunk]:
    """Parse unified diff text into a list of DiffHunk models.

    Multiple hunks within the same file are merged into a single DiffHunk.

    Args:
        diff_text: Raw unified diff output from git.

    Returns:
        List of DiffHunk models, one per changed file.
    """
    if not diff_text.strip():
        return []

    # Split on diff boundaries
    file_diffs = re.split(r"(?=^diff --git )", diff_text, flags=re.MULTILINE)
    file_diffs = [d for d in file_diffs if d.strip()]

    hunks: list[DiffHunk] = []
    for file_diff in file_diffs:
        hunk = _parse_file_diff(file_diff)
        if hunk is not None:
            hunks.append(hunk)

    return hunks


def _parse_file_diff(file_diff: str) -> DiffHunk | None:
    """Parse a single file's diff block into a DiffHunk."""
    header_match = _DIFF_HEADER_RE.search(file_diff)
    if header_match is None:
        return None

    old_path_raw = header_match.group(1)
    new_path_raw = header_match.group(2)

    # Detect rename
    is_rename = False
    rename_from = _RENAME_FROM_RE.search(file_diff)
    rename_to = _RENAME_TO_RE.search(file_diff)
    if rename_from and rename_to:
        is_rename = True
        old_path_raw = rename_from.group(1)
        new_path_raw = rename_to.group(1)

    # Detect binary
    is_binary = bool(_BINARY_RE.search(file_diff))

    # Use new_path as the canonical file_path
    file_path = new_path_raw

    if is_binary or (is_rename and not _HUNK_HEADER_RE.search(file_diff)):
        return DiffHunk(
            file_path=file_path,
            old_path=old_path_raw if old_path_raw != new_path_raw else None,
            new_path=new_path_raw,
            added_lines=[],
            removed_lines=[],
            context_lines=[],
            header="",
            is_rename=is_rename,
            is_copy=False,
            is_binary=is_binary,
        )

    # Parse hunk headers and content lines
    all_added: list[tuple[int, str]] = []
    all_removed: list[tuple[int, str]] = []
    all_context: list[tuple[int, str]] = []
    first_header = ""

    hunk_positions = list(_HUNK_HEADER_RE.finditer(file_diff))
    for idx, hunk_match in enumerate(hunk_positions):
        if idx == 0:
            first_header = hunk_match.group(0)

        old_line = int(hunk_match.group(1))
        new_line = int(hunk_match.group(2))

        # Get lines until next hunk header or end
        start = hunk_match.end()
        end = hunk_positions[idx + 1].start() if idx + 1 < len(hunk_positions) else len(file_diff)

        content = file_diff[start:end]
        for line in content.split("\n"):
            if not line:
                continue
            if line.startswith("+"):
                all_added.append((new_line, line[1:]))
                new_line += 1
            elif line.startswith("-"):
                all_removed.append((old_line, line[1:]))
                old_line += 1
            elif line.startswith(" "):
                all_context.append((new_line, line[1:]))
                old_line += 1
                new_line += 1
            # Lines starting with \ (e.g., "\ No newline at end of file") are skipped

    # Determine old_path / new_path
    old_path: str | None = old_path_raw if old_path_raw != new_path_raw else None
    new_path: str | None = new_path_raw

    return DiffHunk(
        file_path=file_path,
        old_path=old_path,
        new_path=new_path,
        added_lines=all_added,
        removed_lines=all_removed,
        context_lines=all_context,
        header=first_header,
        is_rename=is_rename,
        is_copy=False,
        is_binary=False,
    )
