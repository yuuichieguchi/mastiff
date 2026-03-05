"""TypeScript/JavaScript import parser using regex patterns."""

from __future__ import annotations

import re

# import ... from "..."
_IMPORT_FROM_RE = re.compile(
    r"""import\s+(?:"""
    r"""(?:\{[^}]*\})|"""          # named: import { foo } from "..."
    r"""(?:\*\s+as\s+\w+)|"""     # namespace: import * as X from "..."
    r"""(?:\w+)"""                 # default: import X from "..."
    r""")\s+from\s+["']([^"']+)["']""",
)

# import "..." (side-effect only)
_IMPORT_BARE_RE = re.compile(r"""import\s+["']([^"']+)["']""")

# require("...")
_REQUIRE_RE = re.compile(r"""require\(\s*["']([^"']+)["']\s*\)""")

# import("...")  (dynamic import)
_DYNAMIC_IMPORT_RE = re.compile(r"""import\(\s*["']([^"']+)["']\s*\)""")

# export { ... } from "..."
_RE_EXPORT_RE = re.compile(r"""export\s+\{[^}]*\}\s+from\s+["']([^"']+)["']""")


class TypeScriptImportParser:
    """Extract import module specifiers from TypeScript/JavaScript source code."""

    def parse(self, source: str) -> list[str]:
        """Parse TypeScript/JavaScript source and return imported module specifiers.

        Supports: named imports, default imports, namespace imports, require(),
        dynamic import(), side-effect imports, and re-exports.

        Args:
            source: TypeScript or JavaScript source code string.

        Returns:
            List of module specifier strings.
        """
        modules: list[str] = []
        seen: set[str] = set()

        for pattern in (
            _IMPORT_FROM_RE,
            _IMPORT_BARE_RE,
            _REQUIRE_RE,
            _DYNAMIC_IMPORT_RE,
            _RE_EXPORT_RE,
        ):
            for match in pattern.finditer(source):
                specifier = match.group(1)
                if specifier not in seen:
                    seen.add(specifier)
                    modules.append(specifier)

        return modules
