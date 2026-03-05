"""Review command for the mastiff CLI."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click


@click.command()
@click.argument("commit_range", required=False)
@click.option("--staged", is_flag=True, help="Review staged changes only")
@click.option(
    "--profile",
    type=click.Choice(["quick", "standard", "deep"]),
    default="standard",
    help="Review depth profile",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["terminal", "json"]),
    default="terminal",
    help="Output format",
)
@click.option("--strict", is_flag=True, help="Fail on any finding")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to mastiff.yaml config",
)
@click.pass_context
def review(
    ctx: click.Context,
    commit_range: str | None,
    staged: bool,
    profile: str,
    output_format: str,
    strict: bool,
    config_path: Path | None,
) -> None:
    """Review code changes for dangerous patterns."""
    import os

    from mastiff.analysis.client import AnthropicProvider
    from mastiff.cli.output import render_findings, render_json
    from mastiff.config.loader import load_config
    from mastiff.core.engine import ReviewEngine

    config = load_config(config_path)
    api_key = os.environ.get(config.api.api_key_env, "")
    if not api_key:
        raise click.ClickException(f"Set {config.api.api_key_env} environment variable")

    provider = AnthropicProvider(api_key=api_key, model=config.api.model)
    engine = ReviewEngine(config=config, provider=provider)

    result = asyncio.run(
        engine.review(
            staged=staged,
            commit_range=commit_range,
            profile=profile,
        )
    )

    if output_format == "json":
        click.echo(render_json(result.response))
    else:
        render_findings(result.response, show_confidence=config.output.show_confidence)

    if strict and result.response.findings:
        raise SystemExit(1)
