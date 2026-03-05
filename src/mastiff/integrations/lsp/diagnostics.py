"""Convert mastiff findings to LSP Diagnostic objects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range

from mastiff.core.severity import Severity

if TYPE_CHECKING:
    from mastiff.core.models import FindingSchema


def finding_to_diagnostic(finding: FindingSchema) -> Diagnostic:
    """Convert a FindingSchema to an LSP Diagnostic.

    LSP uses 0-based line numbers, while FindingSchema uses 1-based.

    Args:
        finding: A mastiff finding.

    Returns:
        An LSP Diagnostic.
    """
    severity_map: dict[Severity, DiagnosticSeverity] = {
        Severity.CRITICAL: DiagnosticSeverity.Error,
        Severity.WARNING: DiagnosticSeverity.Warning,
        Severity.INFO: DiagnosticSeverity.Information,
    }

    start_line = max(0, finding.line_start - 1)
    end_line = max(0, (finding.line_end or finding.line_start) - 1)

    return Diagnostic(
        range=Range(
            start=Position(line=start_line, character=finding.column_start or 0),
            end=Position(line=end_line, character=finding.column_end or 0),
        ),
        severity=severity_map.get(finding.severity, DiagnosticSeverity.Warning),
        source="mastiff",
        message=f"[{finding.rule_id}] {finding.title}: {finding.explanation}",
    )
