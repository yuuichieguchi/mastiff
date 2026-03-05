"""Rich terminal output for mastiff review findings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from mastiff.security.sanitizer import sanitize_output

if TYPE_CHECKING:
    from mastiff.core.models import ReviewResponse


def render_findings(
    response: ReviewResponse,
    *,
    show_confidence: bool = True,
    group_by: str = "file",
) -> None:
    """Render review findings as a Rich table to the terminal.

    Args:
        response: ReviewResponse containing findings.
        show_confidence: Whether to show the confidence column.
        group_by: Grouping strategy (file/category/severity).
    """
    console = Console()

    if not response.findings:
        console.print("[green]No issues found.[/green]")
        return

    table = Table(title="Review Findings")
    table.add_column("File", style="cyan")
    table.add_column("Line", style="yellow")
    table.add_column("Severity", style="red")
    table.add_column("Category")
    table.add_column("Title")
    if show_confidence:
        table.add_column("Confidence")

    for finding in sorted(response.findings, key=lambda f: (f.file_path, f.line_start)):
        row = [
            sanitize_output(finding.file_path),
            str(finding.line_start),
            finding.severity.value,
            finding.category.value,
            sanitize_output(finding.title),
        ]
        if show_confidence:
            row.append(f"{finding.confidence:.0%}")
        table.add_row(*row)

    console.print(table)


def render_json(response: ReviewResponse) -> str:
    """Render review response as formatted JSON.

    Args:
        response: ReviewResponse to serialize.

    Returns:
        Indented JSON string.
    """
    return response.model_dump_json(indent=2)
