"""Rich terminal output for mastiff review findings."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from mastiff.core.models import ReviewResponse  # noqa: TC001 (runtime use)
from mastiff.security.sanitizer import sanitize_output


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


def render_agent(response: ReviewResponse) -> str:
    """Render review findings in agent-friendly plain text format.

    Args:
        response: ReviewResponse containing findings.

    Returns:
        Plain text string (no ANSI, no Rich). Empty string if no findings.
    """
    if not response.findings:
        return ""

    parts: list[str] = []
    for finding in response.findings:
        header = (
            f"[{finding.severity.value.upper()}] "
            f"{sanitize_output(finding.file_path)}:{finding.line_start} "
            f"{finding.rule_id}"
        )
        parts.append(header)
        parts.append(sanitize_output(finding.title))
        if finding.suggested_fix:
            parts.append(f"FIX: {finding.suggested_fix}")
        parts.append("")  # blank line separator

    return "\n".join(parts).rstrip("\n")
