"""Init command for the mastiff CLI."""

from __future__ import annotations

from pathlib import Path

import click


@click.command()
def init() -> None:
    """Create a mastiff.yaml configuration file."""
    config_path = Path("mastiff.yaml")
    if config_path.exists():
        raise click.ClickException("mastiff.yaml already exists")

    import yaml

    from mastiff.config.defaults import DEFAULT_CONFIG

    config_path.write_text(
        yaml.dump(DEFAULT_CONFIG, default_flow_style=False, sort_keys=False)
    )
    click.echo(f"Created {config_path}")
