"""Pydantic v2 configuration models for mastiff."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiConfig(BaseModel):
    """API provider configuration."""

    model_config = ConfigDict(extra="forbid")

    model: str | None = None
    max_tokens: int = Field(default=4096, ge=1)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    api_key_env: str = "ANTHROPIC_API_KEY"
    provider: str | None = None


class ContextConfig(BaseModel):
    """Context-gathering configuration."""

    model_config = ConfigDict(extra="forbid")

    max_depth: int = Field(default=2, ge=0)
    max_context_files: int = 20
    max_file_lines: int = 500
    max_diff_lines: int = 3000
    exclude_patterns: list[str] = Field(
        default=["**/*.test.*", "**/node_modules/**", "**/__pycache__/**"],
    )
    path_aliases: dict[str, str] = Field(default_factory=dict)


class DetectionConfig(BaseModel):
    """Detection rules configuration."""

    model_config = ConfigDict(extra="forbid")

    categories: dict[str, bool] = Field(
        default={
            "blocking": True,
            "race_condition": True,
            "degradation": True,
            "resource_leak": True,
            "security": True,
        },
    )
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    severity_threshold: str = "info"
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class SecurityConfig(BaseModel):
    """Security and redaction configuration."""

    model_config = ConfigDict(extra="forbid")

    never_send_paths: list[str] = Field(
        default=[
            ".env",
            "*.pem",
            "*.key",
            "*.p12",
            "*.jks",
            "*.pfx",
            "*credentials*",
            "**/secrets/**",
            "**/.kube/config",
        ],
    )
    redaction_rules: list[str] = Field(default_factory=list)
    entropy_detection: bool = True


class CostConfig(BaseModel):
    """Cost-control configuration."""

    model_config = ConfigDict(extra="forbid")

    max_cost_usd_per_run: float = Field(default=1.0, ge=0)
    max_tokens_per_run: int | None = None
    max_api_seconds: int = Field(default=120, ge=1)


class SuppressionRule(BaseModel):
    """A single suppression rule for ignoring specific findings."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str | None = None
    fingerprint: str | None = None
    file: str | None = None
    reason: str


class ProjectConfig(BaseModel):
    """Project metadata configuration."""

    model_config = ConfigDict(extra="forbid")

    description: str = ""
    architecture: str = ""
    known_patterns: list[str] = Field(default_factory=list)
    custom_rules: list[str] = Field(default_factory=list)


class OutputConfig(BaseModel):
    """Output formatting configuration."""

    model_config = ConfigDict(extra="forbid")

    format: Literal["terminal", "json", "sarif", "agent"] = "terminal"
    color: bool = True
    show_confidence: bool = True
    group_by: Literal["file", "category", "severity"] = "file"


class EditorConfig(BaseModel):
    """Editor integration configuration."""

    model_config = ConfigDict(extra="forbid")

    debounce_ms: int = Field(default=500, ge=0)
    review_on_save: bool = True
    profile: Literal["quick", "standard", "deep"] = "quick"
    cache_max_entries: int = Field(default=200, ge=0)


class PrecommitConfig(BaseModel):
    """Pre-commit hook configuration."""

    model_config = ConfigDict(extra="forbid")

    block_on_critical: bool = True
    block_on_warning: bool = False
    strict: bool = False
    max_review_time_seconds: int = Field(default=60, ge=1)
    max_stale_minutes: int = Field(default=30, ge=1)
    use_baseline: bool = True


class MastiffConfig(BaseModel):
    """Top-level mastiff configuration, aggregating all sub-configs."""

    model_config = ConfigDict(extra="forbid")

    api: ApiConfig = Field(default_factory=ApiConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    cost: CostConfig = Field(default_factory=CostConfig)
    suppressions: list[SuppressionRule] = Field(default_factory=list)
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    editor: EditorConfig = Field(default_factory=EditorConfig)
    precommit: PrecommitConfig = Field(default_factory=PrecommitConfig)
