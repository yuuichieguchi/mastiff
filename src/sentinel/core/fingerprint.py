"""Stable fingerprint generation for sentinel findings."""

from __future__ import annotations

import hashlib
import re

from sentinel.core.models import FindingSchema


def generate_fingerprint(rule_id: str, code_snippet: str) -> str:
    """Generate a stable fingerprint from rule ID and code snippet.

    Whitespace is normalized (strip + collapse internal spaces) so that
    trivial formatting differences do not change the fingerprint.
    """
    normalized = re.sub(r"\s+", " ", code_snippet.strip())
    payload = f"{rule_id}\x00{normalized}"
    return hashlib.sha256(payload.encode()).hexdigest()


def fingerprint_finding(finding: FindingSchema, code_snippet: str) -> str:
    """Generate a fingerprint for a FindingSchema instance."""
    return generate_fingerprint(finding.rule_id, code_snippet)
