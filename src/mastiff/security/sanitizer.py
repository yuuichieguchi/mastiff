"""Sanitization utilities for removing dangerous characters from output text."""

from __future__ import annotations

import re

# ANSI escape sequences: CSI (ESC[...X) and OSC (ESC]...BEL/ST) and other ESC sequences
_ANSI_ESCAPE_RE = re.compile(
    r"\x1b"  # ESC character
    r"(?:"
    r"\[[0-9;]*[A-Za-z]"  # CSI sequences like \x1b[31m
    r"|"
    r"\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC sequences
    r"|"
    r"[()][AB012]"  # Character set selection
    r"|"
    r"[A-Z]"  # Two-character escape sequences like ESC M
    r")"
)

# Control characters except newline (\n = 0x0A) and tab (\t = 0x09)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_output(text: str) -> str:
    """Remove ANSI escape sequences and control characters from text.

    Preserves newlines (\\n) and tabs (\\t) as they are meaningful in output.
    All other control characters (0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F, 0x7F)
    are stripped.

    Args:
        text: Raw text potentially containing escape sequences.

    Returns:
        Cleaned text safe for display.
    """
    # First strip ANSI escape sequences (multi-character)
    result = _ANSI_ESCAPE_RE.sub("", text)
    # Then strip remaining individual control characters
    result = _CONTROL_CHAR_RE.sub("", result)
    return result


def sanitize_for_log(text: str) -> str:
    """Escape control characters for safe log display.

    Unlike sanitize_output which removes control characters, this function
    replaces them with their escaped representation (e.g., \\x1b, \\x00)
    so they are visible in log output.

    Args:
        text: Raw text potentially containing control characters.

    Returns:
        Text with control characters replaced by escape representations.
    """

    def _escape_char(match: re.Match[str]) -> str:
        char = match.group(0)
        code = ord(char)
        return f"\\x{code:02x}"

    # First escape ANSI escape sequences (replace ESC with its repr)
    result = _ANSI_ESCAPE_RE.sub(
        lambda m: m.group(0).replace("\x1b", "\\x1b"),
        text,
    )
    # Then escape remaining control characters
    result = _CONTROL_CHAR_RE.sub(_escape_char, result)
    return result
