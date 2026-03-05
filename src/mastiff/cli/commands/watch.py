"""Watch command for the mastiff CLI — continuous file monitoring."""
from __future__ import annotations

import subprocess
import time

import click


def _has_changes() -> bool:
    """Check if the working tree has changes using git diff-index."""
    result = subprocess.run(
        ["git", "diff-index", "--quiet", "HEAD", "--"],
        capture_output=True,
    )
    return result.returncode != 0


def _adaptive_interval(default_interval: int, consecutive_no_change: int) -> int:
    """Calculate adaptive polling interval with backoff.

    After 10 consecutive no-change polls, double the interval (max 30s).
    """
    if consecutive_no_change >= 10:
        return min(default_interval * 2, 30)
    return default_interval


@click.command()
@click.option(
    "--interval", default=3, type=click.IntRange(min=1),
    help="Polling interval in seconds",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["terminal", "json", "agent"]),
    default="agent",
    help="Output format",
)
@click.option(
    "--profile",
    type=click.Choice(["quick", "standard", "deep"]),
    default="quick",
    help="Review depth profile",
)
def watch(interval: int, output_format: str, profile: str) -> None:
    """Watch for file changes and run incremental reviews."""
    click.echo(f"Watching for changes (interval={interval}s)...")
    consecutive_no_change = 0
    reviewing = False

    try:
        while True:
            current_interval = _adaptive_interval(interval, consecutive_no_change)

            if not reviewing and _has_changes():
                consecutive_no_change = 0
                reviewing = True
                try:
                    result = subprocess.run(
                        ["mastiff", "review", "--format", output_format, "--profile", profile],
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )
                    if result.stdout:
                        click.echo(result.stdout, nl=False)
                    if result.stderr:
                        click.echo(result.stderr, err=True, nl=False)
                except subprocess.TimeoutExpired:
                    click.echo("Review timed out", err=True)
                finally:
                    reviewing = False
            else:
                consecutive_no_change += 1

            time.sleep(current_interval)
    except KeyboardInterrupt:
        click.echo("\nStopped watching.")
