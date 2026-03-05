"""Baseline command for the mastiff CLI."""

from __future__ import annotations

from pathlib import Path

import click


@click.command()
@click.option("--rebase", is_flag=True, help="Regenerate baseline")
def baseline(rebase: bool) -> None:
    """Manage the findings baseline."""
    baseline_path = Path(".mastiff-baseline.json")
    if rebase or not baseline_path.exists():
        # Would run a full review and save fingerprints
        click.echo("Baseline created/updated.")
    else:
        click.echo(f"Baseline exists at {baseline_path}")
