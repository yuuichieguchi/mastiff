"""Tests for mastiff.cli.commands.watch — watch mode."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestWatchDetection:
    """Tests for watch mode change detection."""

    def test_detects_working_tree_changes(self) -> None:
        """Mock git diff-index returning returncode=1 (changes exist).
        Assert _has_changes() is True."""
        from mastiff.cli.commands.watch import _has_changes

        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("mastiff.cli.commands.watch.subprocess.run", return_value=mock_result):
            assert _has_changes() is True

    def test_no_changes_detected(self) -> None:
        """Mock git diff-index returning returncode=0. Assert _has_changes() is False."""
        from mastiff.cli.commands.watch import _has_changes

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("mastiff.cli.commands.watch.subprocess.run", return_value=mock_result):
            assert _has_changes() is False

    def test_adaptive_backoff(self) -> None:
        """After 10 consecutive no-change polls, interval should double. After change, resets."""
        from mastiff.cli.commands.watch import _adaptive_interval

        # Start with default interval of 3
        default_interval = 3

        # After 10 consecutive no-change polls, interval doubles
        interval_after_10 = _adaptive_interval(
            default_interval=default_interval,
            consecutive_no_change=10,
        )
        assert interval_after_10 == default_interval * 2

        # After detecting a change (consecutive_no_change resets to 0), back to original
        interval_after_change = _adaptive_interval(
            default_interval=default_interval,
            consecutive_no_change=0,
        )
        assert interval_after_change == default_interval
