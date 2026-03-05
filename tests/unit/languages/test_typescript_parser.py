"""Tests for mastiff.context.languages.typescript — TypeScript import parser."""


class TestTypeScriptImportParser:
    """TypeScriptImportParser tests using regex."""

    def test_named_import(self):
        from mastiff.context.languages.typescript import TypeScriptImportParser

        parser = TypeScriptImportParser()
        result = parser.parse('import { foo } from "./utils"')
        assert any("utils" in r for r in result)

    def test_default_import(self):
        from mastiff.context.languages.typescript import TypeScriptImportParser

        parser = TypeScriptImportParser()
        result = parser.parse('import React from "react"')
        assert "react" in result

    def test_namespace_import(self):
        from mastiff.context.languages.typescript import TypeScriptImportParser

        parser = TypeScriptImportParser()
        result = parser.parse('import * as path from "path"')
        assert "path" in result

    def test_require(self):
        from mastiff.context.languages.typescript import TypeScriptImportParser

        parser = TypeScriptImportParser()
        result = parser.parse('const fs = require("fs")')
        assert "fs" in result

    def test_dynamic_import(self):
        from mastiff.context.languages.typescript import TypeScriptImportParser

        parser = TypeScriptImportParser()
        result = parser.parse('const mod = await import("./module")')
        assert any("module" in r for r in result)

    def test_re_export(self):
        from mastiff.context.languages.typescript import TypeScriptImportParser

        parser = TypeScriptImportParser()
        result = parser.parse('export { foo } from "./bar"')
        assert any("bar" in r for r in result)

    def test_multiline_import(self):
        from mastiff.context.languages.typescript import TypeScriptImportParser

        parser = TypeScriptImportParser()
        source = 'import {\n  foo,\n  bar\n} from "./utils"'
        result = parser.parse(source)
        assert any("utils" in r for r in result)
