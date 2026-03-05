"""Tests for mastiff.diff — parser, filter, collector."""

import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# diff/parser.py
# ---------------------------------------------------------------------------


class TestDiffParser:
    """parse_diff function tests."""

    def test_simple_modification(self):
        from mastiff.diff.parser import parse_diff

        diff_text = (
            "diff --git a/src/main.py b/src/main.py\n"
            "index abc1234..def5678 100644\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1,3 +1,3 @@\n"
            " line1\n"
            "-old_line\n"
            "+new_line\n"
            " line3\n"
        )
        hunks = parse_diff(diff_text)
        assert len(hunks) == 1
        hunk = hunks[0]
        assert hunk.file_path == "src/main.py"
        assert len(hunk.added_lines) == 1
        assert hunk.added_lines[0][1] == "new_line"
        assert len(hunk.removed_lines) == 1
        assert hunk.removed_lines[0][1] == "old_line"
        assert hunk.is_binary is False
        assert hunk.is_rename is False

    def test_new_file(self):
        from mastiff.diff.parser import parse_diff

        diff_text = (
            "diff --git a/new_file.py b/new_file.py\n"
            "new file mode 100644\n"
            "index 0000000..abc1234\n"
            "--- /dev/null\n"
            "+++ b/new_file.py\n"
            "@@ -0,0 +1,2 @@\n"
            "+line1\n"
            "+line2\n"
        )
        hunks = parse_diff(diff_text)
        assert len(hunks) == 1
        hunk = hunks[0]
        assert hunk.file_path == "new_file.py"
        assert len(hunk.added_lines) == 2
        assert len(hunk.removed_lines) == 0

    def test_deleted_file(self):
        from mastiff.diff.parser import parse_diff

        diff_text = (
            "diff --git a/old_file.py b/old_file.py\n"
            "deleted file mode 100644\n"
            "index abc1234..0000000\n"
            "--- a/old_file.py\n"
            "+++ /dev/null\n"
            "@@ -1,2 +0,0 @@\n"
            "-line1\n"
            "-line2\n"
        )
        hunks = parse_diff(diff_text)
        assert len(hunks) == 1
        hunk = hunks[0]
        assert hunk.file_path == "old_file.py"
        assert len(hunk.removed_lines) == 2
        assert len(hunk.added_lines) == 0

    def test_rename(self):
        from mastiff.diff.parser import parse_diff

        diff_text = (
            "diff --git a/old_name.py b/new_name.py\n"
            "similarity index 100%\n"
            "rename from old_name.py\n"
            "rename to new_name.py\n"
        )
        hunks = parse_diff(diff_text)
        assert len(hunks) == 1
        hunk = hunks[0]
        assert hunk.is_rename is True
        assert hunk.old_path == "old_name.py"
        assert hunk.new_path == "new_name.py"
        assert hunk.file_path == "new_name.py"

    def test_binary(self):
        from mastiff.diff.parser import parse_diff

        diff_text = (
            "diff --git a/image.png b/image.png\n"
            "new file mode 100644\n"
            "index 0000000..abc1234\n"
            "Binary files /dev/null and b/image.png differ\n"
        )
        hunks = parse_diff(diff_text)
        assert len(hunks) == 1
        assert hunks[0].is_binary is True
        assert hunks[0].file_path == "image.png"

    def test_multiple_files(self):
        from mastiff.diff.parser import parse_diff

        diff_text = (
            "diff --git a/file1.py b/file1.py\n"
            "index abc1234..def5678 100644\n"
            "--- a/file1.py\n"
            "+++ b/file1.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old1\n"
            "+new1\n"
            "diff --git a/file2.py b/file2.py\n"
            "index abc1234..def5678 100644\n"
            "--- a/file2.py\n"
            "+++ b/file2.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old2\n"
            "+new2\n"
        )
        hunks = parse_diff(diff_text)
        assert len(hunks) == 2
        paths = {h.file_path for h in hunks}
        assert paths == {"file1.py", "file2.py"}

    def test_multiple_hunks_same_file_merged(self):
        from mastiff.diff.parser import parse_diff

        diff_text = (
            "diff --git a/src/app.py b/src/app.py\n"
            "index abc1234..def5678 100644\n"
            "--- a/src/app.py\n"
            "+++ b/src/app.py\n"
            "@@ -1,3 +1,3 @@\n"
            " context1\n"
            "-removed1\n"
            "+added1\n"
            " context2\n"
            "@@ -10,3 +10,3 @@\n"
            " context3\n"
            "-removed2\n"
            "+added2\n"
            " context4\n"
        )
        hunks = parse_diff(diff_text)
        assert len(hunks) == 1
        hunk = hunks[0]
        assert hunk.file_path == "src/app.py"
        assert len(hunk.added_lines) == 2
        assert len(hunk.removed_lines) == 2

    def test_empty_diff(self):
        from mastiff.diff.parser import parse_diff

        hunks = parse_diff("")
        assert hunks == []


# ---------------------------------------------------------------------------
# diff/filter.py
# ---------------------------------------------------------------------------


class TestDiffFilter:
    """filter_hunks function tests."""

    def _make_hunk(self, file_path: str, *, is_binary: bool = False):
        from mastiff.core.models import DiffHunk

        return DiffHunk(
            file_path=file_path,
            old_path=None,
            new_path=file_path,
            added_lines=[(1, "line")],
            removed_lines=[],
            context_lines=[],
            header="@@ -0,0 +1,1 @@",
            is_binary=is_binary,
        )

    def test_binary_files_filtered(self):
        from mastiff.diff.filter import filter_hunks

        hunks = [
            self._make_hunk("src/main.py"),
            self._make_hunk("image.png", is_binary=True),
        ]
        result = filter_hunks(hunks)
        assert len(result) == 1
        assert result[0].file_path == "src/main.py"

    def test_exclude_patterns_fnmatch(self):
        from mastiff.diff.filter import filter_hunks

        hunks = [
            self._make_hunk("src/main.py"),
            self._make_hunk("node_modules/pkg/index.js"),
            self._make_hunk("src/__pycache__/mod.pyc"),
        ]
        result = filter_hunks(
            hunks,
            exclude_patterns=["**/node_modules/**", "**/__pycache__/**"],
        )
        assert len(result) == 1
        assert result[0].file_path == "src/main.py"

    def test_sensitive_paths(self):
        from mastiff.diff.filter import filter_hunks

        hunks = [
            self._make_hunk("src/main.py"),
            self._make_hunk(".env"),
            self._make_hunk("certs/server.pem"),
        ]
        result = filter_hunks(
            hunks,
            never_send_paths=[".env", "*.pem"],
        )
        assert len(result) == 1
        assert result[0].file_path == "src/main.py"

    def test_no_filters_returns_non_binary(self):
        from mastiff.diff.filter import filter_hunks

        hunks = [
            self._make_hunk("src/main.py"),
            self._make_hunk("image.png", is_binary=True),
        ]
        result = filter_hunks(hunks)
        assert len(result) == 1
        assert result[0].file_path == "src/main.py"

    def test_empty_hunks(self):
        from mastiff.diff.filter import filter_hunks

        result = filter_hunks([])
        assert result == []


# ---------------------------------------------------------------------------
# diff/collector.py
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    """Helper to initialise a git repo with user config and an initial commit."""
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )


class TestDiffCollector:
    """collect_diff function tests."""

    def test_working_changes(self, tmp_path: Path):
        from mastiff.diff.collector import collect_diff

        _init_git_repo(tmp_path)
        # Create initial commit
        (tmp_path / "file.py").write_text("x = 1\n")
        subprocess.run(
            ["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-m", "init"],
            check=True,
            capture_output=True,
        )
        # Modify file (unstaged)
        (tmp_path / "file.py").write_text("x = 2\n")
        hunks = collect_diff(cwd=tmp_path)
        assert len(hunks) >= 1
        assert any(h.file_path == "file.py" for h in hunks)

    def test_staged_changes(self, tmp_path: Path):
        from mastiff.diff.collector import collect_diff

        _init_git_repo(tmp_path)
        (tmp_path / "file.py").write_text("x = 1\n")
        subprocess.run(
            ["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-m", "init"],
            check=True,
            capture_output=True,
        )
        (tmp_path / "file.py").write_text("x = 2\n")
        subprocess.run(
            ["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True
        )
        hunks = collect_diff(staged=True, cwd=tmp_path)
        assert len(hunks) >= 1
        assert any(h.file_path == "file.py" for h in hunks)

    def test_commit_range(self, tmp_path: Path):
        from mastiff.diff.collector import collect_diff

        _init_git_repo(tmp_path)
        (tmp_path / "file.py").write_text("v1\n")
        subprocess.run(
            ["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-m", "c1"],
            check=True,
            capture_output=True,
        )
        (tmp_path / "file.py").write_text("v2\n")
        subprocess.run(
            ["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-m", "c2"],
            check=True,
            capture_output=True,
        )
        hunks = collect_diff(commit_range="HEAD~1..HEAD", cwd=tmp_path)
        assert len(hunks) >= 1

    def test_empty_repo_returns_empty(self, tmp_path: Path):
        from mastiff.diff.collector import collect_diff

        _init_git_repo(tmp_path)
        hunks = collect_diff(cwd=tmp_path)
        assert hunks == []
