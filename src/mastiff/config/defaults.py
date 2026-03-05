"""Default configuration values for mastiff."""

from __future__ import annotations

DEFAULT_CONFIG: dict[str, object] = {
    "api": {
        "model": "claude-opus-4-20250514",
        "max_tokens": 4096,
        "temperature": 0.2,
        "api_key_env": "ANTHROPIC_API_KEY",
        "provider": None,
    },
    "context": {
        "max_depth": 2,
        "max_context_files": 20,
        "max_file_lines": 500,
        "max_diff_lines": 3000,
        "exclude_patterns": ["**/*.test.*", "**/node_modules/**", "**/__pycache__/**"],
        "path_aliases": {},
    },
    "detection": {
        "categories": {
            "blocking": True,
            "race_condition": True,
            "degradation": True,
            "resource_leak": True,
            "security": True,
        },
        "min_confidence": 0.6,
        "severity_threshold": "info",
        "score_threshold": 0.5,
    },
    "security": {
        "never_send_paths": [
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
        "redaction_rules": [],
        "entropy_detection": True,
    },
    "cost": {
        "max_cost_usd_per_run": 1.0,
        "max_tokens_per_run": None,
        "max_api_seconds": 120,
    },
    "suppressions": [],
    "project": {
        "description": "",
        "architecture": "",
        "known_patterns": [],
        "custom_rules": [],
    },
    "output": {
        "format": "terminal",
        "color": True,
        "show_confidence": True,
        "group_by": "file",
    },
    "editor": {
        "debounce_ms": 500,
        "review_on_save": True,
        "profile": "quick",
        "cache_max_entries": 200,
    },
    "precommit": {
        "block_on_critical": True,
        "block_on_warning": False,
        "strict": False,
        "max_review_time_seconds": 60,
        "max_stale_minutes": 30,
        "use_baseline": True,
    },
}
