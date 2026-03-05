"""Import resolver that maps import specifiers to file paths."""

from __future__ import annotations

from pathlib import Path


class ImportResolver:
    """Resolve import module names to file paths on disk.

    Supports relative imports, package directories, and path aliases.

    Args:
        root: Project root directory.
        path_aliases: Mapping of alias prefixes to directory paths
                      relative to root (e.g., ``{"@": "src"}``).
    """

    _EXTENSIONS = (".py", ".ts", ".tsx", ".js", ".jsx")

    def __init__(
        self,
        root: Path,
        path_aliases: dict[str, str] | None = None,
    ) -> None:
        self._root = root
        self._path_aliases = path_aliases or {}

    def resolve(self, specifier: str, source_file: Path) -> Path | None:
        """Resolve an import specifier to a file path.

        Args:
            specifier: The import module name or path.
            source_file: The file containing the import statement.

        Returns:
            Resolved Path if found, None otherwise.
        """
        # Handle path aliases (e.g., "@/utils" -> "src/utils")
        for alias, target_dir in self._path_aliases.items():
            if specifier.startswith(alias + "/"):
                rest = specifier[len(alias) + 1 :]
                resolved = self._root / target_dir / rest
                found = self._try_resolve(resolved)
                if found is not None:
                    return found

        # Handle relative imports (./foo, ../foo)
        if specifier.startswith("."):
            base_dir = source_file.parent
            resolved = base_dir / specifier.lstrip("./")
            found = self._try_resolve(resolved)
            if found is not None:
                return found

        # Handle as absolute/package import from root
        parts = specifier.replace(".", "/")
        resolved = self._root / parts
        found = self._try_resolve(resolved)
        if found is not None:
            return found

        return None

    def _try_resolve(self, path: Path) -> Path | None:
        """Try resolving a path by checking extensions and package __init__."""
        # Direct file match
        if path.is_file():
            return path

        # Try with extensions
        for ext in self._EXTENSIONS:
            candidate = path.with_suffix(ext)
            if candidate.is_file():
                return candidate

        # Try as package directory
        if path.is_dir():
            init = path / "__init__.py"
            if init.is_file():
                return init
            index = path / "index.ts"
            if index.is_file():
                return index
            index_js = path / "index.js"
            if index_js.is_file():
                return index_js

        return None
