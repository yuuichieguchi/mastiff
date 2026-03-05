"""Python import parser using the ast module."""

from __future__ import annotations

import ast


class PythonImportParser:
    """Extract import module names from Python source code using ast.parse."""

    def parse(self, source: str) -> list[str]:
        """Parse Python source code and return imported module names.

        Uses ``ast.parse()`` to walk the AST for ``Import`` and ``ImportFrom``
        nodes. Returns the top-level module name for ``import X`` statements
        and the module name for ``from X import ...`` statements.

        Relative imports (e.g., ``from . import utils``) return the dot
        prefix as the module name.

        Returns an empty list on ``SyntaxError``.

        Args:
            source: Python source code string.

        Returns:
            List of imported module name strings.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None:
                    prefix = "." * (node.level or 0)
                    modules.append(f"{prefix}{node.module}")
                elif node.level:
                    # from . import something
                    modules.append("." * node.level)

        return modules
