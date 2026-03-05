"""Tests for mastiff.context.languages.python — Python import parser."""


class TestPythonImportParser:
    """PythonImportParser tests using ast module."""

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
        result = parser.parse("from .utils import helper")
        assert any("utils" in r for r in result)

    def test_multiple_imports(self):
        from mastiff.context.languages.python import PythonImportParser

        parser = PythonImportParser()
        source = "import os\nimport sys\nfrom pathlib import Path"
        result = parser.parse(source)
        assert "os" in result
        assert "sys" in result
        assert "pathlib" in result

    def test_multiline_import(self):
        from mastiff.context.languages.python import PythonImportParser

        parser = PythonImportParser()
        source = "from os import (\n    path,\n    getcwd\n)"
        result = parser.parse(source)
        assert "os" in result

    def test_invalid_syntax_returns_empty(self):
        from mastiff.context.languages.python import PythonImportParser

        parser = PythonImportParser()
        result = parser.parse("def broken(:")
        assert result == []

    def test_ignores_comments(self):
        from mastiff.context.languages.python import PythonImportParser

        parser = PythonImportParser()
        source = "# import os\nimport sys"
        result = parser.parse(source)
        assert "os" not in result
        assert "sys" in result
