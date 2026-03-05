"""Git operation utilities built on the subprocess runner."""

from __future__ import annotations

from pathlib import Path

from mastiff._internal.subprocess import SubprocessError, run_command


class GitError(Exception):
    """Raised when a git operation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


def git_command(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: float = 30.0,
) -> str:
    """Run a git command and return its stripped stdout.

    Args:
        args: Git sub-command and arguments (without the leading ``git``).
        cwd: Working directory for the git process.
        timeout: Maximum seconds to wait.

    Returns:
        Stripped stdout from the git command.

    Raises:
        GitError: If the git command exits with a non-zero code.
    """
    try:
        result = run_command(["git", *args], cwd=cwd, timeout=timeout)
    except SubprocessError as exc:
        raise GitError(str(exc)) from exc
    return result.stdout.strip()


def get_repo_root(cwd: Path | None = None) -> Path:
    """Return the root directory of the git repository.

    Args:
        cwd: Directory to start searching from.

    Returns:
        Absolute Path to the repository root.

    Raises:
        GitError: If the directory is not inside a git repository.
    """
    try:
        root = git_command(["rev-parse", "--show-toplevel"], cwd=cwd)
    except GitError:
        raise GitError(f"Not a git repository: {cwd}") from None
    return Path(root)


def is_git_repo(cwd: Path | None = None) -> bool:
    """Check whether the given directory is inside a git repository.

    Args:
        cwd: Directory to check.

    Returns:
        True if inside a git repo, False otherwise.
    """
    try:
        run_command(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=cwd,
            check=True,
        )
    except SubprocessError:
        return False
    return True


def get_diff(
    *,
    staged: bool = False,
    commit_range: str | None = None,
    cwd: Path | None = None,
) -> str:
    """Return git diff output.

    Args:
        staged: If True, show only staged changes (``git diff --cached``).
        commit_range: If provided, diff between commits (e.g. ``HEAD~1..HEAD``).
        cwd: Working directory for the git process.

    Returns:
        The diff output as a string.
    """
    if commit_range is not None:
        return git_command(["diff", commit_range], cwd=cwd)
    if staged:
        return git_command(["diff", "--cached"], cwd=cwd)
    return git_command(["diff", "HEAD"], cwd=cwd)
