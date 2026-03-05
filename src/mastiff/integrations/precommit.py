"""Pre-commit hook entry point for mastiff."""

from __future__ import annotations

import os
import sys


def main() -> None:
    """Pre-commit hook entry point."""
    from click.testing import CliRunner

    from mastiff.cli.commands.review import review

    strict = os.environ.get("CI", "").lower() in ("true", "1")
    runner = CliRunner()
    args = ["--staged"]
    if strict:
        args.append("--strict")
    result = runner.invoke(review, args)
    if result.exit_code != 0:
        print(result.output, file=sys.stderr)
        sys.exit(result.exit_code)
    print(result.output)
