"""Compiled regex patterns for detecting secrets and credentials in text."""

from __future__ import annotations

import re

# Patterns that match specific well-known secret formats and generic credential assignments.
# Each pattern is compiled with IGNORECASE where appropriate.
SECRET_PATTERNS: list[re.Pattern[str]] = [
    # OpenAI API keys: sk- followed by at least 16 chars
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    # GitHub personal access tokens: ghp_ followed by at least 20 alphanumeric chars
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    # GitHub OAuth tokens
    re.compile(r"gho_[A-Za-z0-9]{20,}"),
    # GitHub user-to-server tokens
    re.compile(r"ghu_[A-Za-z0-9]{20,}"),
    # GitHub server-to-server tokens
    re.compile(r"ghs_[A-Za-z0-9]{20,}"),
    # GitHub refresh tokens
    re.compile(r"ghr_[A-Za-z0-9]{20,}"),
    # AWS access key IDs: AKIA followed by 16 uppercase alphanumeric chars
    re.compile(r"AKIA[0-9A-Z]{16}"),
    # Bearer tokens in authorization headers
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    # Generic secret assignments: api_key, secret_key, api_secret, etc.
    # Requires the value to be at least 8 chars to avoid false positives
    re.compile(
        r"""(?:api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?key|auth[_-]?token)"""
        r"""\s*[=:]\s*["'][^"']{8,}["']""",
        re.IGNORECASE,
    ),
    # Password assignments with string values at least 8 chars
    re.compile(
        r"""(?:password|passwd|pwd)\s*[=:]\s*["'][^"']{8,}["']""",
        re.IGNORECASE,
    ),
    # Private key headers
    re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
]
