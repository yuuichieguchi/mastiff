"""Install command for the mastiff CLI."""

from __future__ import annotations

from pathlib import Path

import click


@click.command()
def install() -> None:
    """Install mastiff as a git pre-commit hook."""
    hooks_dir = Path(".git/hooks")
    if not hooks_dir.exists():
        raise click.ClickException("Not a git repository")

    hook_path = hooks_dir / "pre-commit"
    hook_content = "#!/bin/sh\nmastiff review --staged --strict\n"
    hook_path.write_text(hook_content)
    hook_path.chmod(0o755)
    click.echo(f"Installed pre-commit hook at {hook_path}")
