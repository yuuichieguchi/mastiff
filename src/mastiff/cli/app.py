"""Click entry point for the mastiff CLI."""

from __future__ import annotations

import click

from mastiff.cli.commands.baseline import baseline
from mastiff.cli.commands.init import init
from mastiff.cli.commands.install import install
from mastiff.cli.commands.review import review
from mastiff.cli.commands.server import server


@click.group()
@click.version_option(package_name="mastiff")
def main() -> None:
    """Mastiff — AI code review agent."""


main.add_command(review)
main.add_command(init)
main.add_command(install)
main.add_command(baseline)
main.add_command(server)
