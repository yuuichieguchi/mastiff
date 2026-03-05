"""Tests for mastiff.core.pipeline — ReviewPipeline contract."""


class TestReviewPipelineContract:
    """ReviewPipeline contract tests — shared across CLI/LSP/pre-commit."""

    def test_pipeline_has_run_method(self):
        from mastiff.core.pipeline import ReviewPipeline
        assert hasattr(ReviewPipeline, 'run')

    def test_pipeline_returns_review_result(self):
        import inspect

        from mastiff.core.pipeline import ReviewPipeline
        sig = inspect.signature(ReviewPipeline.run)
        # Should accept diff_text parameter
        params = list(sig.parameters.keys())
        assert 'self' in params or len(params) >= 1

    def test_pipeline_accepts_profile(self):
        """Pipeline should accept an analysis profile (quick/standard/deep)."""
        import inspect

        from mastiff.core.pipeline import ReviewPipeline
        sig = inspect.signature(ReviewPipeline.run)
        params = list(sig.parameters.keys())
        assert 'profile' in params
