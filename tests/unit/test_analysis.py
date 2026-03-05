"""Tests for mastiff.analysis — categories, prompt, response, client."""

import json

# ---------------------------------------------------------------------------
# analysis/categories.py
# ---------------------------------------------------------------------------


class TestCategoryDefinitions:
    """CATEGORY_DEFINITIONS dict tests."""

    def test_has_all_categories(self):
        from mastiff.analysis.categories import CATEGORY_DEFINITIONS

        expected = {"blocking", "race_condition", "degradation", "resource_leak", "security"}
        assert set(CATEGORY_DEFINITIONS.keys()) == expected

    def test_each_has_name_description_examples(self):
        from mastiff.analysis.categories import CATEGORY_DEFINITIONS

        for key, value in CATEGORY_DEFINITIONS.items():
            assert "name" in value, f"{key} missing 'name'"
            assert "description" in value, f"{key} missing 'description'"
            assert "examples" in value, f"{key} missing 'examples'"
            assert isinstance(value["name"], str)
            assert isinstance(value["description"], str)
            assert isinstance(value["examples"], list)
            assert len(value["examples"]) > 0


# ---------------------------------------------------------------------------
# analysis/prompt.py
# ---------------------------------------------------------------------------


class TestPromptBuilder:
    """PromptBuilder tests."""

    def test_basic_prompt(self):
        from mastiff.analysis.prompt import PromptBuilder

        builder = PromptBuilder(profile="standard")
        prompt = builder.build(diff_text="+ new line", context_text="existing code")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_system_priority_instruction(self):
        from mastiff.analysis.prompt import PromptBuilder

        builder = PromptBuilder(profile="standard")
        prompt = builder.build(diff_text="+ x = 1", context_text="")
        # Should contain priority/system instruction about review focus
        assert "PRIORITY" in prompt or "priority" in prompt or "review" in prompt.lower()

    def test_diff_tags(self):
        from mastiff.analysis.prompt import PromptBuilder

        builder = PromptBuilder(profile="standard")
        prompt = builder.build(diff_text="+ added", context_text="context")
        assert "<diff>" in prompt
        assert "</diff>" in prompt
        assert "+ added" in prompt

    def test_context_tags(self):
        from mastiff.analysis.prompt import PromptBuilder

        builder = PromptBuilder(profile="standard")
        prompt = builder.build(diff_text="diff", context_text="some context")
        assert "<context>" in prompt
        assert "</context>" in prompt
        assert "some context" in prompt

    def test_output_schema(self):
        from mastiff.analysis.prompt import PromptBuilder

        builder = PromptBuilder(profile="standard")
        prompt = builder.build(diff_text="diff", context_text="ctx")
        # Should describe expected JSON output format
        assert "schema_version" in prompt or "findings" in prompt

    def test_profile_token_limits_quick(self):
        from mastiff.analysis.prompt import PromptBuilder

        builder = PromptBuilder(profile="quick")
        assert builder.max_diff_tokens == 5000
        assert builder.max_context_tokens == 3000

    def test_profile_token_limits_standard(self):
        from mastiff.analysis.prompt import PromptBuilder

        builder = PromptBuilder(profile="standard")
        assert builder.max_diff_tokens == 20000
        assert builder.max_context_tokens == 15000

    def test_profile_token_limits_deep(self):
        from mastiff.analysis.prompt import PromptBuilder

        builder = PromptBuilder(profile="deep")
        assert builder.max_diff_tokens == 50000
        assert builder.max_context_tokens == 30000

    def test_truncation(self):
        from mastiff.analysis.prompt import PromptBuilder

        builder = PromptBuilder(profile="quick")
        # Create a diff that exceeds the token budget
        long_diff = "+" + "x" * 100000
        prompt = builder.build(diff_text=long_diff, context_text="ctx")
        # The prompt should be shorter than the original diff
        assert len(prompt) < len(long_diff)

    def test_categories_in_prompt(self):
        from mastiff.analysis.prompt import PromptBuilder

        builder = PromptBuilder(profile="standard")
        prompt = builder.build(diff_text="diff", context_text="ctx")
        # Should mention detection categories
        assert "blocking" in prompt.lower() or "race" in prompt.lower()

    def test_project_context(self):
        from mastiff.analysis.prompt import PromptBuilder

        builder = PromptBuilder(profile="standard", project_context="A FastAPI web app")
        prompt = builder.build(diff_text="diff", context_text="ctx")
        assert "FastAPI web app" in prompt


# ---------------------------------------------------------------------------
# analysis/response.py
# ---------------------------------------------------------------------------


class TestResponseParser:
    """parse_response function tests."""

    def test_valid_response(self):
        from mastiff.analysis.response import parse_response

        data = {
            "schema_version": "1",
            "findings": [],
        }
        result = parse_response(json.dumps(data))
        assert result is not None
        assert result.findings == []

    def test_with_findings(self):
        from mastiff.analysis.response import parse_response

        data = {
            "schema_version": "1",
            "findings": [
                {
                    "rule_id": "blocking-sync",
                    "category": "blocking",
                    "severity": "critical",
                    "file_path": "main.py",
                    "line_start": 10,
                    "title": "Blocking call",
                    "explanation": "time.sleep blocks",
                    "confidence": 0.9,
                }
            ],
        }
        result = parse_response(json.dumps(data))
        assert result is not None
        assert len(result.findings) == 1
        assert result.findings[0].rule_id == "blocking-sync"

    def test_invalid_json(self):
        from mastiff.analysis.response import parse_response

        result = parse_response("not json {{{")
        assert result is None

    def test_incomplete_json(self):
        from mastiff.analysis.response import parse_response

        result = parse_response('{"schema_version": "1"}')
        assert result is None

    def test_extra_fields_rejected(self):
        from mastiff.analysis.response import parse_response

        data = {
            "schema_version": "1",
            "findings": [],
            "extra_field": "bad",
        }
        result = parse_response(json.dumps(data))
        assert result is None

    def test_markdown_extraction(self):
        from mastiff.analysis.response import parse_response

        data = {
            "schema_version": "1",
            "findings": [],
        }
        markdown = f"Here is the result:\n```json\n{json.dumps(data)}\n```\n"
        result = parse_response(markdown)
        assert result is not None
        assert result.findings == []

    def test_invalid_confidence(self):
        from mastiff.analysis.response import parse_response

        data = {
            "schema_version": "1",
            "findings": [
                {
                    "rule_id": "test",
                    "category": "blocking",
                    "severity": "warning",
                    "file_path": "x.py",
                    "line_start": 1,
                    "title": "t",
                    "explanation": "e",
                    "confidence": 5.0,  # Invalid: > 1.0
                }
            ],
        }
        result = parse_response(json.dumps(data))
        assert result is None


# ---------------------------------------------------------------------------
# analysis/client.py
# ---------------------------------------------------------------------------


class TestCostGuard:
    """CostGuard budget enforcement tests."""

    def test_under_budget(self):
        from mastiff.analysis.client import CostGuard

        guard = CostGuard(max_cost_usd=1.0, max_tokens=100000)
        assert guard.check(estimated_cost=0.5, tokens=50000) is True

    def test_over_budget_cost(self):
        from mastiff.analysis.client import CostGuard

        guard = CostGuard(max_cost_usd=1.0, max_tokens=100000)
        assert guard.check(estimated_cost=1.5, tokens=50000) is False

    def test_over_budget_tokens(self):
        from mastiff.analysis.client import CostGuard

        guard = CostGuard(max_cost_usd=1.0, max_tokens=100000)
        assert guard.check(estimated_cost=0.5, tokens=150000) is False


class TestAnthropicProvider:
    """AnthropicProvider basic structure tests."""

    def test_has_review_method(self):
        from mastiff.analysis.client import AnthropicProvider

        provider = AnthropicProvider(api_key="test-key", model="claude-opus-4-20250514")
        assert hasattr(provider, "review")
        assert callable(provider.review)

    def test_accepts_model_api_key_params(self):
        from mastiff.analysis.client import AnthropicProvider

        provider = AnthropicProvider(api_key="sk-test", model="claude-sonnet-4-20250514")
        assert provider.model == "claude-sonnet-4-20250514"
        assert provider.api_key == "sk-test"
