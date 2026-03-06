"""Install command for the mastiff CLI."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import click

_MASTIFF_LINE = "mastiff review --staged --strict"


def _atomic_write(path: Path, content: str, mode: int = 0o755) -> None:
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


def _has_mastiff_line(text: str) -> bool:
    """Check if mastiff command exists as an active (non-commented) line."""
    return any(line.strip() == _MASTIFF_LINE for line in text.splitlines())


@click.command()
@click.option("--claude-code", is_flag=True, help="Install Claude Code PostToolUse hooks")
@click.option("--codex", is_flag=True, help="Install Codex CLI post-commit hook")
def install(claude_code: bool, codex: bool) -> None:
    """Install mastiff hooks for git or AI agents."""
    if claude_code:
        from mastiff.integrations.claude_code import install_hooks

        install_hooks(Path.cwd())
        click.echo("Installed Claude Code hooks")
        return

    if codex:
        from mastiff.integrations.codex import install_hooks

        hooks_dir = Path(".git/hooks")
        if not hooks_dir.exists():
            raise click.ClickException("Not a git repository")
        install_hooks(Path.cwd())
        click.echo("Installed Codex post-commit hook")
        return

    # Default: install pre-commit hook
    hooks_dir = Path(".git/hooks")
    if not hooks_dir.exists():
        raise click.ClickException("Not a git repository")

    hook_path = hooks_dir / "pre-commit"

    if hook_path.exists():
        existing = hook_path.read_text()
        if _has_mastiff_line(existing):
            click.echo("mastiff pre-commit hook is already installed")
            return
        click.echo(f"Warning: existing pre-commit hook found at {hook_path}, appending mastiff")
        _atomic_write(hook_path, existing.rstrip("\n") + "\n" + _MASTIFF_LINE + "\n")
    else:
        _atomic_write(hook_path, "#!/bin/sh\n" + _MASTIFF_LINE + "\n")

    click.echo(f"Installed pre-commit hook at {hook_path}")
