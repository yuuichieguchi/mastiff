"""Claude Code hook integration for mastiff."""
from __future__ import annotations

import json
import os
import tempfile
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from pathlib import Path

_MARKER_START = "# --- mastiff-hook-start ---"
_MARKER_END = "# --- mastiff-hook-end ---"

_HOOK_SCRIPT = """\
#!/bin/sh
# --- mastiff-hook-start ---
# Mastiff PostToolUse hook for Claude Code
# Reads tool_input.file_path from stdin, reviews working-tree diff
FILE_PATH=$(cat | python3 -c "import sys,json; d=json.load(sys.stdin); \
print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)
if [ -z "$FILE_PATH" ]; then
    exit 0
fi
RESULT=$(mastiff review --format agent --profile quick 2>&1)
EXIT_CODE=$?
if [ $EXIT_CODE -eq 1 ]; then
    echo "mastiff: internal error" >&2
    exit 0
fi
if [ $EXIT_CODE -eq 2 ] || [ -n "$RESULT" ]; then
    echo "$RESULT" >&2
    exit 2
fi
exit 0
# --- mastiff-hook-end ---
"""

_MASTIFF_HOOK_ENTRY: dict[str, object] = {
    "matcher": "Edit|Write",
    "hooks": [
        {
            "type": "command",
            "command": ".claude/hooks/mastiff-review.sh",
            "timeout": 30,
            "statusMessage": "Mastiff reviewing...",
        }
    ],
}


def install_hooks(project_dir: Path) -> None:
    """Install Claude Code PostToolUse hooks for mastiff.

    Creates:
    - .claude/hooks/mastiff-review.sh (executable hook script)
    - .claude/settings.local.json (merged with existing settings)
    """
    hooks_dir = project_dir / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Write hook script atomically
    hook_path = hooks_dir / "mastiff-review.sh"
    _atomic_write(hook_path, _HOOK_SCRIPT, mode=0o755)

    # Merge settings.local.json
    settings_path = project_dir / ".claude" / "settings.local.json"
    _merge_settings(settings_path)


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


def _merge_settings(settings_path: Path) -> None:
    """Merge Mastiff hook entry into settings.local.json."""
    if settings_path.exists():
        raw = settings_path.read_text()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise click.ClickException(
                f"Corrupt .claude/settings.local.json: {exc}. Fix manually or delete to regenerate."
            ) from None
    else:
        data = {}

    hooks = data.setdefault("hooks", {})
    post_tool_use: list[dict[str, object]] = hooks.setdefault("PostToolUse", [])

    # Check if Mastiff entry already exists (idempotent)
    for entry in post_tool_use:
        if _is_mastiff_entry(entry):
            return

    post_tool_use.append(_MASTIFF_HOOK_ENTRY)
    _atomic_write(settings_path, json.dumps(data, indent=2) + "\n")


def _is_mastiff_entry(entry: dict[str, object]) -> bool:
    """Check if a hook entry is a Mastiff entry."""
    hooks_list = entry.get("hooks", [])
    if not isinstance(hooks_list, list):
        return False
    for hook in hooks_list:
        if isinstance(hook, dict) and "mastiff-review.sh" in str(hook.get("command", "")):
            return True
    return False
