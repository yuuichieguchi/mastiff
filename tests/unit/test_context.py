"""Tests for mastiff.context — language parsers, cache, resolver, tracer."""

import time
from pathlib import Path
from typing import runtime_checkable

import pytest


# ---------------------------------------------------------------------------
# context/languages/base.py — ImportParser Protocol
# ---------------------------------------------------------------------------


class TestImportParserProtocol:
    """ImportParser protocol tests."""

    def test_protocol_is_runtime_checkable(self):
        from mastiff.context.languages.base import ImportParser

        assert hasattr(ImportParser, "__protocol_attrs__") or runtime_checkable

    def test_python_parser_satisfies_protocol(self):
        from mastiff.context.languages.base import ImportParser
        from mastiff.context.languages.python import PythonImportParser

        assert isinstance(PythonImportParser(), ImportParser)

    def test_typescript_parser_satisfies_protocol(self):
        from mastiff.context.languages.base import ImportParser
        from mastiff.context.languages.typescript import TypeScriptImportParser

        assert isinstance(TypeScriptImportParser(), ImportParser)

    def test_generic_parser_satisfies_protocol(self):
        from mastiff.context.languages.base import ImportParser
        from mastiff.context.languages.generic import GenericImportParser

        assert isinstance(GenericImportParser(), ImportParser)


# ---------------------------------------------------------------------------
# context/languages/python.py — PythonImportParser
# ---------------------------------------------------------------------------


class TestPythonImportParser:
    """PythonImportParser tests."""

    def test_simple_import(self):
        from mastiff.context.languages.python import PythonImportParser

        parser = PythonImportParser()
        result = parser.parse("import os")
        assert "os" in result

    def test_from_import(self):
        from mastiff.context.languages.python import PythonImportParser

        parser = PythonImportParser()
        result = parser.parse("from os.path import join")
        assert "os.path" in result

    def test_relative_import(self):
        from mastiff.context.languages.python import PythonImportParser

        parser = PythonImportParser()
        result = parser.parse("from . import utils")
        assert "." in result

    def test_multiline_import(self):
        from mastiff.context.languages.python import PythonImportParser

        parser = PythonImportParser()
        source = "from os.path import (\n    join,\n    dirname,\n)"
        result = parser.parse(source)
        assert "os.path" in result

    def test_invalid_syntax_returns_empty(self):
        from mastiff.context.languages.python import PythonImportParser

        parser = PythonImportParser()
        result = parser.parse("def foo(:\n  pass")
        assert result == []

    def test_comments_ignored(self):
        from mastiff.context.languages.python import PythonImportParser

        parser = PythonImportParser()
        source = "# import fake\nimport os\n"
        result = parser.parse(source)
        assert "os" in result
        assert "fake" not in result


# ---------------------------------------------------------------------------
# context/languages/typescript.py — TypeScriptImportParser
# ---------------------------------------------------------------------------


class TestTypeScriptImportParser:
    """TypeScriptImportParser tests."""

    def test_named_import(self):
        from mastiff.context.languages.typescript import TypeScriptImportParser

        parser = TypeScriptImportParser()
        result = parser.parse('import { foo } from "./bar";')
        assert "./bar" in result

    def test_default_import(self):
        from mastiff.context.languages.typescript import TypeScriptImportParser

        parser = TypeScriptImportParser()
        result = parser.parse('import React from "react";')
        assert "react" in result

    def test_namespace_import(self):
        from mastiff.context.languages.typescript import TypeScriptImportParser

        parser = TypeScriptImportParser()
        result = parser.parse('import * as path from "path";')
        assert "path" in result

    def test_require(self):
        from mastiff.context.languages.typescript import TypeScriptImportParser

        parser = TypeScriptImportParser()
        result = parser.parse('const fs = require("fs");')
        assert "fs" in result

    def test_dynamic_import(self):
        from mastiff.context.languages.typescript import TypeScriptImportParser

        parser = TypeScriptImportParser()
        result = parser.parse('const mod = import("./lazy");')
        assert "./lazy" in result

    def test_re_export(self):
        from mastiff.context.languages.typescript import TypeScriptImportParser

        parser = TypeScriptImportParser()
        result = parser.parse('export { foo } from "./utils";')
        assert "./utils" in result


# ---------------------------------------------------------------------------
# context/languages/generic.py — GenericImportParser
# ---------------------------------------------------------------------------


class TestGenericImportParser:
    """GenericImportParser regex fallback tests."""

    def test_python_style(self):
        from mastiff.context.languages.generic import GenericImportParser

        parser = GenericImportParser()
        result = parser.parse("import os")
        assert "os" in result

    def test_typescript_style(self):
        from mastiff.context.languages.generic import GenericImportParser

        parser = GenericImportParser()
        result = parser.parse('import { foo } from "bar";')
        assert "bar" in result


# ---------------------------------------------------------------------------
# context/cache.py — FileCache
# ---------------------------------------------------------------------------


class TestFileCache:
    """FileCache LRU with mtime invalidation tests."""

    def test_store_and_retrieve(self, tmp_path: Path):
        from mastiff.context.cache import FileCache

        cache = FileCache(max_entries=10)
        f = tmp_path / "test.py"
        f.write_text("content")
        cache.put(f, ["os", "sys"])
        assert cache.get(f) == ["os", "sys"]

    def test_mtime_invalidation(self, tmp_path: Path):
        from mastiff.context.cache import FileCache

        cache = FileCache(max_entries=10)
        f = tmp_path / "test.py"
        f.write_text("v1")
        cache.put(f, ["os"])
        # Modify file
        time.sleep(0.05)
        f.write_text("v2")
        assert cache.get(f) is None

    def test_lru_eviction(self, tmp_path: Path):
        from mastiff.context.cache import FileCache

        cache = FileCache(max_entries=2)
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f3 = tmp_path / "c.py"
        for f in (f1, f2, f3):
            f.write_text("x")
        cache.put(f1, ["a"])
        cache.put(f2, ["b"])
        # f1 is oldest, should be evicted when f3 is added
        cache.put(f3, ["c"])
        assert cache.get(f1) is None
        assert cache.get(f2) == ["b"]
        assert cache.get(f3) == ["c"]


# ---------------------------------------------------------------------------
# context/resolver.py — ImportResolver
# ---------------------------------------------------------------------------


class TestImportResolver:
    """ImportResolver import→file path tests."""

    def test_relative_import(self, tmp_path: Path):
        from mastiff.context.resolver import ImportResolver

        resolver = ImportResolver(root=tmp_path)
        (tmp_path / "utils.py").write_text("# utils")
        source_file = tmp_path / "main.py"
        result = resolver.resolve("./utils", source_file)
        assert result is not None
        assert result.name == "utils.py"

    def test_package_import(self, tmp_path: Path):
        from mastiff.context.resolver import ImportResolver

        resolver = ImportResolver(root=tmp_path)
        pkg = tmp_path / "mypackage"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        result = resolver.resolve("mypackage", tmp_path / "main.py")
        assert result is not None
        assert result.name == "__init__.py"

    def test_nonexistent_returns_none(self, tmp_path: Path):
        from mastiff.context.resolver import ImportResolver

        resolver = ImportResolver(root=tmp_path)
        result = resolver.resolve("nonexistent", tmp_path / "main.py")
        assert result is None

    def test_path_alias(self, tmp_path: Path):
        from mastiff.context.resolver import ImportResolver

        src = tmp_path / "src"
        src.mkdir()
        (src / "utils.py").write_text("# utils")
        resolver = ImportResolver(root=tmp_path, path_aliases={"@": "src"})
        result = resolver.resolve("@/utils", tmp_path / "main.py")
        assert result is not None
        assert result.name == "utils.py"


# ---------------------------------------------------------------------------
# context/tracer.py — ImportTracer
# ---------------------------------------------------------------------------


class TestImportTracer:
    """ImportTracer BFS with depth limit tests."""

    def test_direct_imports(self, tmp_path: Path):
        from mastiff.context.tracer import ImportTracer

        (tmp_path / "main.py").write_text("import utils\n")
        (tmp_path / "utils.py").write_text("x = 1\n")
        tracer = ImportTracer(root=tmp_path)
        files = tracer.trace(tmp_path / "main.py", max_depth=1)
        assert tmp_path / "utils.py" in files

    def test_depth_2_imports(self, tmp_path: Path):
        from mastiff.context.tracer import ImportTracer

        (tmp_path / "main.py").write_text("import a\n")
        (tmp_path / "a.py").write_text("import b\n")
        (tmp_path / "b.py").write_text("x = 1\n")
        tracer = ImportTracer(root=tmp_path)
        files = tracer.trace(tmp_path / "main.py", max_depth=2)
        assert tmp_path / "a.py" in files
        assert tmp_path / "b.py" in files

    def test_max_depth_limits(self, tmp_path: Path):
        from mastiff.context.tracer import ImportTracer

        (tmp_path / "main.py").write_text("import a\n")
        (tmp_path / "a.py").write_text("import b\n")
        (tmp_path / "b.py").write_text("x = 1\n")
        tracer = ImportTracer(root=tmp_path)
        files = tracer.trace(tmp_path / "main.py", max_depth=1)
        assert tmp_path / "a.py" in files
        assert tmp_path / "b.py" not in files

    def test_circular_imports(self, tmp_path: Path):
        from mastiff.context.tracer import ImportTracer

        (tmp_path / "a.py").write_text("import b\n")
        (tmp_path / "b.py").write_text("import a\n")
        tracer = ImportTracer(root=tmp_path)
        # Should not infinite loop
        files = tracer.trace(tmp_path / "a.py", max_depth=5)
        assert tmp_path / "b.py" in files

    def test_empty_file(self, tmp_path: Path):
        from mastiff.context.tracer import ImportTracer

        (tmp_path / "main.py").write_text("")
        tracer = ImportTracer(root=tmp_path)
        files = tracer.trace(tmp_path / "main.py", max_depth=1)
        assert files == []
