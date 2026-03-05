"""ImportParser protocol for language-specific import extraction."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ImportParser(Protocol):
    """Protocol for extracting import module names from source code."""

    def parse(self, source: str) -> list[str]:
        """Parse source code and return a list of imported module names.

        Args:
            source: The source code to parse.

        Returns:
            List of module name strings found in import statements.
        """
        ...
