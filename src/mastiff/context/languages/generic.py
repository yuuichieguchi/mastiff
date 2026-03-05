"""Generic import parser using regex fallback for unknown languages."""

from __future__ import annotations

import re

# Python-style: import X / from X import ...
_PYTHON_IMPORT_RE = re.compile(r"^\s*import\s+(\w[\w.]*)", re.MULTILINE)
_PYTHON_FROM_RE = re.compile(r"^\s*from\s+(\w[\w.]*)\s+import", re.MULTILINE)

# JS/TS-style: import ... from "..." / require("...")
_JS_FROM_RE = re.compile(r"""from\s+["']([^"']+)["']""")
_JS_REQUIRE_RE = re.compile(r"""require\(\s*["']([^"']+)["']\s*\)""")


class GenericImportParser:
    """Regex-based fallback import parser for unknown file types."""

    def parse(self, source: str) -> list[str]:
        """Parse source code using heuristic regex patterns.

        Args:
            source: Source code string.

        Returns:
            List of module name strings.
        """
        modules: list[str] = []
        seen: set[str] = set()

        for pattern in (_PYTHON_IMPORT_RE, _PYTHON_FROM_RE, _JS_FROM_RE, _JS_REQUIRE_RE):
            for match in pattern.finditer(source):
                name = match.group(1)
                if name not in seen:
                    seen.add(name)
                    modules.append(name)

        return modules
