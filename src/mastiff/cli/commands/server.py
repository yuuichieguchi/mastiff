"""Server command for the mastiff CLI."""

from __future__ import annotations

import click


@click.command()
@click.option("--port", default=0, help="Port for LSP (0 = stdio)")
def server(port: int) -> None:
    """Start the LSP server."""
    click.echo("Starting LSP server...")
    # Will be implemented in integrations/lsp
