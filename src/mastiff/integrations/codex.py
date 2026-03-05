"""Codex CLI hook integration for mastiff."""
from __future__ import annotations

import os
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_MARKER_START = "# --- mastiff-hook-start ---"
_MARKER_END = "# --- mastiff-hook-end ---"

_MASTIFF_BLOCK = """\
# --- mastiff-hook-start ---
# Mastiff review
RESULT=$(mastiff review HEAD~1..HEAD --format agent --profile quick 2>&1)
EXIT_CODE=$?
if [ $EXIT_CODE -eq 2 ]; then
    echo "$RESULT"
fi
# --- mastiff-hook-end ---"""


def install_hooks(project_dir: Path) -> None:
    """Install Codex CLI post-commit hook for mastiff."""
    hooks_dir = project_dir / ".git" / "hooks"
    hook_path = hooks_dir / "post-commit"

    if hook_path.exists():
        existing = hook_path.read_text()
        if _MARKER_START in existing:
            return  # Already installed (idempotent)
        # Backup existing hook
        backup_path = hooks_dir / "post-commit.pre-mastiff"
        backup_path.write_text(existing)
        backup_path.chmod(0o755)
        # Create chained hook
        content = _make_chained_hook()
    else:
        content = _make_standalone_hook()

    _atomic_write(hook_path, content, mode=0o755)


def _make_chained_hook() -> str:
    return f"""\
#!/bin/sh
# Chained post-commit hook (Mastiff + existing)
# Run existing hook if backed up
if [ -f ".git/hooks/post-commit.pre-mastiff" ]; then
    .git/hooks/post-commit.pre-mastiff
fi
{_MASTIFF_BLOCK}
"""


def _make_standalone_hook() -> str:
    return f"""\
#!/bin/sh
{_MASTIFF_BLOCK}
"""


def _atomic_write(path: Path, content: str, mode: int = 0o644) -> None:
    """Write file atomically using tempfile + os.replace."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
