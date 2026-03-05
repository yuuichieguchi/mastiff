"""Subprocess execution utilities with timeout and error handling."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class SubprocessError(Exception):
    """Raised when a subprocess exits with a non-zero return code."""

    def __init__(
        self,
        args: list[str],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        self.args_list = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        cmd = " ".join(args)
        super().__init__(
            f"Command {cmd!r} exited with code {returncode}: {stderr.strip()}"
        )


class SubprocessTimeoutError(SubprocessError):
    """Raised when a subprocess exceeds its timeout."""

    def __init__(self, args: list[str], timeout: float) -> None:
        self.timeout = timeout
        cmd = " ".join(args)
        # Bypass SubprocessError.__init__ because we have no stdout/stderr
        Exception.__init__(self, f"Command {cmd!r} timed out after {timeout}s")
        self.args_list = args
        self.returncode = -1
        self.stdout = ""
        self.stderr = ""


def run_command(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: float = 30.0,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with timeout, capturing stdout/stderr as text.

    Args:
        args: Command and arguments to execute.
        cwd: Working directory for the subprocess.
        timeout: Maximum seconds to wait before killing the process.
        check: If True, raise SubprocessError on non-zero exit code.

    Returns:
        CompletedProcess with stdout and stderr as strings.

    Raises:
        SubprocessTimeoutError: If the command exceeds the timeout.
        SubprocessError: If the command exits with a non-zero code and check is True.
    """
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise SubprocessTimeoutError(args, timeout) from None

    if check and result.returncode != 0:
        raise SubprocessError(
            args=args,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    return result
