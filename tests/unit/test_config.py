"""Tests for mastiff.config — defaults, schema, loader."""

from pathlib import Path

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# config/defaults.py
# ---------------------------------------------------------------------------


class TestDefaultConfig:
    """DEFAULT_CONFIG dict must contain all expected top-level keys and values."""

    def test_default_config_has_all_top_level_keys(self):
        from mastiff.config.defaults import DEFAULT_CONFIG

        expected_keys = {
            "api",
            "context",
            "detection",
            "security",
            "cost",
            "suppressions",
            "project",
            "output",
            "editor",
            "precommit",
        }
        assert set(DEFAULT_CONFIG.keys()) == expected_keys

    # -- api --

    def test_api_defaults(self):
        from mastiff.config.defaults import DEFAULT_CONFIG

        api = DEFAULT_CONFIG["api"]
        assert api["model"] is None
        assert api["max_tokens"] == 4096
        assert api["temperature"] == 0.2
        assert api["api_key_env"] == "ANTHROPIC_API_KEY"
        assert api["provider"] is None

    # -- context --

    def test_context_defaults(self):
        from mastiff.config.defaults import DEFAULT_CONFIG

        ctx = DEFAULT_CONFIG["context"]
        assert ctx["max_depth"] == 2
        assert ctx["max_context_files"] == 20
        assert ctx["max_file_lines"] == 500
        assert ctx["max_diff_lines"] == 3000

    # -- detection --

    def test_detection_defaults(self):
        from mastiff.config.defaults import DEFAULT_CONFIG

        det = DEFAULT_CONFIG["detection"]
        for cat in ("blocking", "race_condition", "degradation", "resource_leak", "security"):
            assert det["categories"][cat] is True
        assert det["min_confidence"] == 0.6
        assert det["severity_threshold"] == "info"
        assert det["score_threshold"] == 0.5

    # -- security --

    def test_security_defaults(self):
        from mastiff.config.defaults import DEFAULT_CONFIG

        sec = DEFAULT_CONFIG["security"]
        assert isinstance(sec["never_send_paths"], list)
        assert len(sec["never_send_paths"]) > 0
        assert ".env" in sec["never_send_paths"]
        assert sec["entropy_detection"] is True

    # -- cost --

    def test_cost_defaults(self):
        from mastiff.config.defaults import DEFAULT_CONFIG

        cost = DEFAULT_CONFIG["cost"]
        assert cost["max_cost_usd_per_run"] == 1.0
        assert cost["max_tokens_per_run"] is None
        assert cost["max_api_seconds"] == 120

    # -- output --

    def test_output_defaults(self):
        from mastiff.config.defaults import DEFAULT_CONFIG

        out = DEFAULT_CONFIG["output"]
        assert out["format"] == "terminal"
        assert out["color"] is True
        assert out["group_by"] == "file"

    # -- editor --

    def test_editor_defaults(self):
        from mastiff.config.defaults import DEFAULT_CONFIG

        ed = DEFAULT_CONFIG["editor"]
        assert ed["debounce_ms"] == 500
        assert ed["profile"] == "quick"
        assert ed["cache_max_entries"] == 200

    # -- precommit --

    def test_precommit_defaults(self):
        from mastiff.config.defaults import DEFAULT_CONFIG

        pc = DEFAULT_CONFIG["precommit"]
        assert pc["block_on_critical"] is True
        assert pc["strict"] is False
        assert pc["max_stale_minutes"] == 30


# ---------------------------------------------------------------------------
# config/schema.py — Pydantic v2 models
# ---------------------------------------------------------------------------


class TestApiConfig:
    """ApiConfig model tests."""

    def test_defaults(self):
        from mastiff.config.schema import ApiConfig

        cfg = ApiConfig()
        assert cfg.model is None
        assert cfg.max_tokens == 4096
        assert cfg.temperature == 0.2
        assert cfg.api_key_env == "ANTHROPIC_API_KEY"
        assert cfg.provider is None

    def test_extra_fields_rejected(self):
        from mastiff.config.schema import ApiConfig

        with pytest.raises(ValidationError):
            ApiConfig(unknown="bad")

    def test_max_tokens_ge_1(self):
        from mastiff.config.schema import ApiConfig

        with pytest.raises(ValidationError):
            ApiConfig(max_tokens=0)

    def test_temperature_bounds(self):
        from mastiff.config.schema import ApiConfig

        with pytest.raises(ValidationError):
            ApiConfig(temperature=-0.1)
        with pytest.raises(ValidationError):
            ApiConfig(temperature=1.1)


class TestContextConfig:
    """ContextConfig model tests."""

    def test_defaults(self):
        from mastiff.config.schema import ContextConfig

        cfg = ContextConfig()
        assert cfg.max_depth == 2
        assert cfg.max_context_files == 20
        assert cfg.max_file_lines == 500
        assert cfg.max_diff_lines == 3000
        assert cfg.exclude_patterns == [
            "**/*.test.*",
            "**/node_modules/**",
            "**/__pycache__/**",
        ]
        assert cfg.path_aliases == {}

    def test_extra_fields_rejected(self):
        from mastiff.config.schema import ContextConfig

        with pytest.raises(ValidationError):
            ContextConfig(unknown="bad")

    def test_max_depth_ge_0(self):
        from mastiff.config.schema import ContextConfig

        with pytest.raises(ValidationError):
            ContextConfig(max_depth=-1)


class TestDetectionConfig:
    """DetectionConfig model tests."""

    def test_defaults(self):
        from mastiff.config.schema import DetectionConfig

        cfg = DetectionConfig()
        assert cfg.categories == {
            "blocking": True,
            "race_condition": True,
            "degradation": True,
            "resource_leak": True,
            "security": True,
        }
        assert cfg.min_confidence == 0.6
        assert cfg.severity_threshold == "info"
        assert cfg.score_threshold == 0.5

    def test_extra_fields_rejected(self):
        from mastiff.config.schema import DetectionConfig

        with pytest.raises(ValidationError):
            DetectionConfig(unknown="bad")

    def test_min_confidence_bounds(self):
        from mastiff.config.schema import DetectionConfig

        with pytest.raises(ValidationError):
            DetectionConfig(min_confidence=-0.1)
        with pytest.raises(ValidationError):
            DetectionConfig(min_confidence=1.1)

    def test_score_threshold_bounds(self):
        from mastiff.config.schema import DetectionConfig

        with pytest.raises(ValidationError):
            DetectionConfig(score_threshold=-0.1)
        with pytest.raises(ValidationError):
            DetectionConfig(score_threshold=1.1)


class TestSecurityConfig:
    """SecurityConfig model tests."""

    def test_defaults(self):
        from mastiff.config.schema import SecurityConfig

        cfg = SecurityConfig()
        assert ".env" in cfg.never_send_paths
        assert isinstance(cfg.redaction_rules, list)
        assert cfg.entropy_detection is True

    def test_extra_fields_rejected(self):
        from mastiff.config.schema import SecurityConfig

        with pytest.raises(ValidationError):
            SecurityConfig(unknown="bad")


class TestCostConfig:
    """CostConfig model tests."""

    def test_defaults(self):
        from mastiff.config.schema import CostConfig

        cfg = CostConfig()
        assert cfg.max_cost_usd_per_run == 1.0
        assert cfg.max_tokens_per_run is None
        assert cfg.max_api_seconds == 120

    def test_extra_fields_rejected(self):
        from mastiff.config.schema import CostConfig

        with pytest.raises(ValidationError):
            CostConfig(unknown="bad")

    def test_max_cost_ge_0(self):
        from mastiff.config.schema import CostConfig

        with pytest.raises(ValidationError):
            CostConfig(max_cost_usd_per_run=-1.0)

    def test_max_api_seconds_ge_1(self):
        from mastiff.config.schema import CostConfig

        with pytest.raises(ValidationError):
            CostConfig(max_api_seconds=0)

    def test_max_tokens_per_run_optional(self):
        from mastiff.config.schema import CostConfig

        cfg = CostConfig(max_tokens_per_run=5000)
        assert cfg.max_tokens_per_run == 5000


class TestSuppressionRule:
    """SuppressionRule model tests."""

    def test_minimal(self):
        from mastiff.config.schema import SuppressionRule

        rule = SuppressionRule(reason="false positive")
        assert rule.reason == "false positive"
        assert rule.rule_id is None
        assert rule.fingerprint is None
        assert rule.file is None

    def test_full(self):
        from mastiff.config.schema import SuppressionRule

        rule = SuppressionRule(
            rule_id="blocking-sync-in-async",
            fingerprint="abc123",
            file="src/main.py",
            reason="intended behavior",
        )
        assert rule.rule_id == "blocking-sync-in-async"
        assert rule.fingerprint == "abc123"
        assert rule.file == "src/main.py"

    def test_extra_fields_rejected(self):
        from mastiff.config.schema import SuppressionRule

        with pytest.raises(ValidationError):
            SuppressionRule(reason="ok", unknown="bad")


class TestProjectConfig:
    """ProjectConfig model tests."""

    def test_defaults(self):
        from mastiff.config.schema import ProjectConfig

        cfg = ProjectConfig()
        assert cfg.description == ""
        assert cfg.architecture == ""
        assert cfg.known_patterns == []
        assert cfg.custom_rules == []

    def test_extra_fields_rejected(self):
        from mastiff.config.schema import ProjectConfig

        with pytest.raises(ValidationError):
            ProjectConfig(unknown="bad")


class TestOutputConfig:
    """OutputConfig model tests."""

    def test_defaults(self):
        from mastiff.config.schema import OutputConfig

        cfg = OutputConfig()
        assert cfg.format == "terminal"
        assert cfg.color is True
        assert cfg.show_confidence is True
        assert cfg.group_by == "file"

    def test_extra_fields_rejected(self):
        from mastiff.config.schema import OutputConfig

        with pytest.raises(ValidationError):
            OutputConfig(unknown="bad")

    def test_format_literal(self):
        from mastiff.config.schema import OutputConfig

        with pytest.raises(ValidationError):
            OutputConfig(format="xml")

    def test_group_by_literal(self):
        from mastiff.config.schema import OutputConfig

        with pytest.raises(ValidationError):
            OutputConfig(group_by="author")


class TestEditorConfig:
    """EditorConfig model tests."""

    def test_defaults(self):
        from mastiff.config.schema import EditorConfig

        cfg = EditorConfig()
        assert cfg.debounce_ms == 500
        assert cfg.review_on_save is True
        assert cfg.profile == "quick"
        assert cfg.cache_max_entries == 200

    def test_extra_fields_rejected(self):
        from mastiff.config.schema import EditorConfig

        with pytest.raises(ValidationError):
            EditorConfig(unknown="bad")

    def test_debounce_ms_ge_0(self):
        from mastiff.config.schema import EditorConfig

        with pytest.raises(ValidationError):
            EditorConfig(debounce_ms=-1)

    def test_profile_literal(self):
        from mastiff.config.schema import EditorConfig

        with pytest.raises(ValidationError):
            EditorConfig(profile="ultra")

    def test_cache_max_entries_ge_0(self):
        from mastiff.config.schema import EditorConfig

        with pytest.raises(ValidationError):
            EditorConfig(cache_max_entries=-1)


class TestPrecommitConfig:
    """PrecommitConfig model tests."""

    def test_defaults(self):
        from mastiff.config.schema import PrecommitConfig

        cfg = PrecommitConfig()
        assert cfg.block_on_critical is True
        assert cfg.block_on_warning is False
        assert cfg.strict is False
        assert cfg.max_review_time_seconds == 60
        assert cfg.max_stale_minutes == 30
        assert cfg.use_baseline is True

    def test_extra_fields_rejected(self):
        from mastiff.config.schema import PrecommitConfig

        with pytest.raises(ValidationError):
            PrecommitConfig(unknown="bad")

    def test_max_review_time_seconds_ge_1(self):
        from mastiff.config.schema import PrecommitConfig

        with pytest.raises(ValidationError):
            PrecommitConfig(max_review_time_seconds=0)

    def test_max_stale_minutes_ge_1(self):
        from mastiff.config.schema import PrecommitConfig

        with pytest.raises(ValidationError):
            PrecommitConfig(max_stale_minutes=0)


class TestMastiffConfig:
    """MastiffConfig top-level model tests."""

    def test_all_defaults(self):
        from mastiff.config.schema import MastiffConfig

        cfg = MastiffConfig()
        assert cfg.api.model is None
        assert cfg.context.max_depth == 2
        assert cfg.detection.min_confidence == 0.6
        assert cfg.security.entropy_detection is True
        assert cfg.cost.max_cost_usd_per_run == 1.0
        assert cfg.suppressions == []
        assert cfg.project.description == ""
        assert cfg.output.format == "terminal"
        assert cfg.editor.debounce_ms == 500
        assert cfg.precommit.block_on_critical is True

    def test_extra_fields_rejected(self):
        from mastiff.config.schema import MastiffConfig

        with pytest.raises(ValidationError):
            MastiffConfig(unknown="bad")

    def test_partial_override(self):
        from mastiff.config.schema import ApiConfig, MastiffConfig

        cfg = MastiffConfig(api=ApiConfig(model="claude-sonnet-4-20250514"))
        assert cfg.api.model == "claude-sonnet-4-20250514"
        # Other defaults remain
        assert cfg.api.max_tokens == 4096
        assert cfg.context.max_depth == 2


# ---------------------------------------------------------------------------
# config/loader.py
# ---------------------------------------------------------------------------


class TestFindConfigFile:
    """find_config_file searches upward for mastiff.yaml."""

    def test_finds_file_in_current_dir(self, tmp_path: Path):
        from mastiff.config.loader import find_config_file

        config_file = tmp_path / "mastiff.yaml"
        config_file.write_text("api:\n  model: test\n")
        result = find_config_file(tmp_path)
        assert result == config_file

    def test_finds_file_in_parent_dir(self, tmp_path: Path):
        from mastiff.config.loader import find_config_file

        config_file = tmp_path / "mastiff.yaml"
        config_file.write_text("api:\n  model: test\n")
        child = tmp_path / "sub" / "deep"
        child.mkdir(parents=True)
        result = find_config_file(child)
        assert result == config_file

    def test_returns_none_when_not_found(self, tmp_path: Path):
        from mastiff.config.loader import find_config_file

        result = find_config_file(tmp_path)
        assert result is None


class TestLoadConfig:
    """load_config merges YAML with defaults via MastiffConfig."""

    def test_no_file_returns_defaults(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        from mastiff.config.loader import load_config
        from mastiff.config.schema import MastiffConfig

        monkeypatch.chdir(tmp_path)
        cfg = load_config(path=None)
        default = MastiffConfig()
        assert cfg.api.model == default.api.model
        assert cfg.context.max_depth == default.context.max_depth

    def test_explicit_path_loads(self, tmp_path: Path):
        from mastiff.config.loader import load_config

        config_file = tmp_path / "mastiff.yaml"
        config_file.write_text("api:\n  model: custom-model\n")
        cfg = load_config(path=config_file)
        assert cfg.api.model == "custom-model"

    def test_partial_yaml_merges_with_defaults(self, tmp_path: Path):
        from mastiff.config.loader import load_config

        config_file = tmp_path / "mastiff.yaml"
        config_file.write_text("cost:\n  max_cost_usd_per_run: 5.0\n")
        cfg = load_config(path=config_file)
        assert cfg.cost.max_cost_usd_per_run == 5.0
        # Other defaults remain
        assert cfg.api.model is None
        assert cfg.context.max_depth == 2

    def test_invalid_yaml_raises_error(self, tmp_path: Path):
        from mastiff.config.loader import load_config

        config_file = tmp_path / "mastiff.yaml"
        config_file.write_text("api:\n  max_tokens: -5\n")
        with pytest.raises(ValidationError):
            load_config(path=config_file)

    def test_empty_yaml_returns_defaults(self, tmp_path: Path):
        from mastiff.config.loader import load_config
        from mastiff.config.schema import MastiffConfig

        config_file = tmp_path / "mastiff.yaml"
        config_file.write_text("")
        cfg = load_config(path=config_file)
        default = MastiffConfig()
        assert cfg.api.model == default.api.model

    def test_auto_detects_config_file_when_path_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_config(None) should auto-detect mastiff.yaml via find_config_file."""
        config_file = tmp_path / "mastiff.yaml"
        config_file.write_text("api:\n  provider: codex\n")
        monkeypatch.chdir(tmp_path)

        from mastiff.config.loader import load_config

        cfg = load_config(path=None)
        assert cfg.api.provider == "codex"

    def test_extra_top_level_key_raises_validation_error(self, tmp_path: Path):
        from mastiff.config.loader import load_config

        config_file = tmp_path / "mastiff.yaml"
        config_file.write_text("unknown_section:\n  key: value\n")
        with pytest.raises(ValidationError):
            load_config(path=config_file)
