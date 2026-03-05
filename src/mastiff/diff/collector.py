"""Collect diff hunks from a git repository."""

from __future__ import annotations

from pathlib import Path

from mastiff._internal.git import GitError, get_diff, is_git_repo
from mastiff.core.models import DiffHunk
from mastiff.diff.parser import parse_diff


def collect_diff(
    *,
    staged: bool = False,
    commit_range: str | None = None,
    cwd: Path | None = None,
) -> list[DiffHunk]:
    """Collect diff hunks from a git repository.

    Args:
        staged: If True, collect only staged changes.
        commit_range: If provided, diff between commits.
        cwd: Working directory for the git process.

    Returns:
        List of DiffHunk models parsed from the diff output.
        Returns empty list if not in a git repo or diff fails.
    """
    if not is_git_repo(cwd=cwd):
        return []

    try:
        diff_text = get_diff(staged=staged, commit_range=commit_range, cwd=cwd)
    except GitError:
        return []

    return parse_diff(diff_text)
