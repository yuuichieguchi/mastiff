"""Pydantic data models for sentinel core domain."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sentinel.core.severity import Severity


class DetectionCategory(Enum):
    """Categories of dangerous code patterns detected by sentinel."""

    BLOCKING = "blocking"
    RACE_CONDITION = "race_condition"
    DEGRADATION = "degradation"
    RESOURCE_LEAK = "resource_leak"


class FindingSchema(BaseModel):
    """A single finding detected during code review."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    rule_id: str
    category: DetectionCategory
    severity: Severity
    file_path: str
    line_start: int
    line_end: int | None = None
    column_start: int | None = None
    column_end: int | None = None
    symbol: str | None = None
    title: str
    explanation: str
    suggested_fix: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class ReviewResponse(BaseModel):
    """Structured response from LLM review containing findings."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    findings: list[FindingSchema]


class DiffHunk(BaseModel):
    """A single hunk from a unified diff."""

    model_config = ConfigDict(extra="forbid")

    file_path: str
    old_path: str | None
    new_path: str | None
    added_lines: list[tuple[int, str]]
    removed_lines: list[tuple[int, str]]
    context_lines: list[tuple[int, str]]
    header: str
    is_rename: bool = False
    is_copy: bool = False
    is_binary: bool = False


class ReviewResult(BaseModel):
    """Full result of a review pipeline run, including metadata."""

    model_config = ConfigDict(extra="forbid")

    response: ReviewResponse
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    model: str
    estimated_cost_usd: float = Field(ge=0)
