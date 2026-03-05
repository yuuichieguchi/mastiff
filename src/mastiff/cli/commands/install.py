"""Install command for the mastiff CLI."""
from __future__ import annotations

from pathlib import Path

import click


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
    hook_content = "#!/bin/sh\nmastiff review --staged --strict\n"
    hook_path.write_text(hook_content)
    hook_path.chmod(0o755)
    click.echo(f"Installed pre-commit hook at {hook_path}")
