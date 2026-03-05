"""Tests for mastiff._internal — subprocess runner and git operations."""

import subprocess
from pathlib import Path

import pytest


class TestRunCommand:
    """run_command function tests."""

    def test_successful_command(self):
        from mastiff._internal.subprocess import run_command

        result = run_command(["echo", "hello"])
        assert result.stdout.strip() == "hello"
        assert result.returncode == 0

    def test_command_with_cwd(self, tmp_path: Path):
        from mastiff._internal.subprocess import run_command

        result = run_command(["pwd"], cwd=tmp_path)
        # On macOS, /tmp is symlinked to /private/tmp
        assert tmp_path.name in result.stdout

    def test_failed_command_raises(self):
        from mastiff._internal.subprocess import SubprocessError, run_command

        with pytest.raises(SubprocessError):
            run_command(["false"])

    def test_failed_command_no_check(self):
        from mastiff._internal.subprocess import run_command

        result = run_command(["false"], check=False)
        assert result.returncode != 0

    def test_timeout_raises(self):
        from mastiff._internal.subprocess import SubprocessTimeoutError, run_command

        with pytest.raises(SubprocessTimeoutError):
            run_command(["sleep", "10"], timeout=0.1)

    def test_stderr_captured(self):
        from mastiff._internal.subprocess import run_command

        result = run_command(
            ["python3", "-c", "import sys; sys.stderr.write('err')"], check=False
        )
        assert "err" in result.stderr


class TestGitCommand:
    """git_command function tests."""

    def test_git_version(self):
        from mastiff._internal.git import git_command

        result = git_command(["--version"])
        assert "git version" in result

    def test_git_command_in_repo(self, tmp_path: Path):
        from mastiff._internal.git import git_command

        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        result = git_command(["status"], cwd=tmp_path)
        assert "On branch" in result or "No commits" in result


class TestGetRepoRoot:
    """get_repo_root function tests."""

    def test_finds_repo_root(self, tmp_path: Path):
        from mastiff._internal.git import get_repo_root

        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subdir = tmp_path / "a" / "b"
        subdir.mkdir(parents=True)
        root = get_repo_root(cwd=subdir)
        assert root == tmp_path

    def test_not_git_repo_raises(self, tmp_path: Path):
        from mastiff._internal.git import GitError, get_repo_root

        with pytest.raises(GitError):
            get_repo_root(cwd=tmp_path)


class TestIsGitRepo:
    """is_git_repo function tests."""

    def test_true_in_repo(self, tmp_path: Path):
        from mastiff._internal.git import is_git_repo

        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        assert is_git_repo(cwd=tmp_path) is True

    def test_false_outside_repo(self, tmp_path: Path):
        from mastiff._internal.git import is_git_repo

        assert is_git_repo(cwd=tmp_path) is False


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


class TestGetDiff:
    """get_diff function tests."""

    def test_diff_head(self, tmp_path: Path):
        from mastiff._internal.git import get_diff

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
        # Modify file
        (tmp_path / "file.py").write_text("x = 2\n")
        diff = get_diff(cwd=tmp_path)
        assert "x = 1" in diff or "x = 2" in diff

    def test_diff_staged(self, tmp_path: Path):
        from mastiff._internal.git import get_diff

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
        diff = get_diff(staged=True, cwd=tmp_path)
        assert "x = 2" in diff

    def test_diff_commit_range(self, tmp_path: Path):
        from mastiff._internal.git import get_diff

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
        diff = get_diff(commit_range="HEAD~1..HEAD", cwd=tmp_path)
        assert "v2" in diff
