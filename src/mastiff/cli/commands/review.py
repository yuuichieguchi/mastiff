"""Review command for the mastiff CLI."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from mastiff.analysis.errors import ProviderError
from mastiff.analysis.provider_factory import create_provider
from mastiff.cli.output import render_agent, render_findings, render_json
from mastiff.config.loader import load_config
from mastiff.core.engine import ReviewEngine


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
    type=click.Choice(["terminal", "json", "agent"]),
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
    config = load_config(config_path)

    try:
        provider = create_provider(config)
    except ProviderError as exc:
        raise click.ClickException(str(exc)) from None

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
    elif output_format == "agent":
        output = render_agent(result.response)
        if output:
            click.echo(output, err=True)
        if result.response.findings:
            raise SystemExit(2)
    else:
        render_findings(result.response, show_confidence=config.output.show_confidence)

    if strict and result.response.findings:
        raise SystemExit(2)
