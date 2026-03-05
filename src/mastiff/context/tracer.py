"""Import tracer using BFS to discover transitive dependencies."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from mastiff.context.languages.generic import GenericImportParser
from mastiff.context.languages.python import PythonImportParser
from mastiff.context.languages.typescript import TypeScriptImportParser
from mastiff.context.resolver import ImportResolver


class ImportTracer:
    """Trace imports from a starting file using BFS with depth limiting.

    Args:
        root: Project root directory for import resolution.
        path_aliases: Optional path alias mapping for the resolver.
    """

    _PYTHON_EXTENSIONS = frozenset((".py", ".pyi"))
    _TS_EXTENSIONS = frozenset((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"))

    def __init__(
        self,
        root: Path,
        path_aliases: dict[str, str] | None = None,
    ) -> None:
        self._root = root
        self._resolver = ImportResolver(root=root, path_aliases=path_aliases)
        self._python_parser = PythonImportParser()
        self._ts_parser = TypeScriptImportParser()
        self._generic_parser = GenericImportParser()

    def trace(self, start_file: Path, *, max_depth: int = 2) -> list[Path]:
        """Trace imports from start_file using BFS up to max_depth.

        Args:
            start_file: The file to start tracing from.
            max_depth: Maximum depth of transitive imports to follow.

        Returns:
            List of discovered file paths (excluding the start file).
        """
        visited: set[Path] = {start_file.resolve()}
        result: list[Path] = []
        queue: deque[tuple[Path, int]] = deque([(start_file, 0)])

        while queue:
            current_file, depth = queue.popleft()
            if depth >= max_depth:
                continue

            imports = self._get_imports(current_file)
            for specifier in imports:
                resolved = self._resolver.resolve(specifier, current_file)
                if resolved is None:
                    continue

                resolved = resolved.resolve()
                if resolved in visited:
                    continue

                visited.add(resolved)
                result.append(resolved)
                queue.append((resolved, depth + 1))

        return result

    def _get_imports(self, file_path: Path) -> list[str]:
        """Extract import specifiers from a file."""
        try:
            source = file_path.read_text(encoding="utf-8")
        except OSError:
            return []

        suffix = file_path.suffix
        if suffix in self._PYTHON_EXTENSIONS:
            return self._python_parser.parse(source)
        if suffix in self._TS_EXTENSIONS:
            return self._ts_parser.parse(source)
        return self._generic_parser.parse(source)
