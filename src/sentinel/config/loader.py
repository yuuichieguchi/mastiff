"""Configuration file discovery and loading for sentinel."""

from __future__ import annotations

from pathlib import Path

import yaml

from sentinel.config.schema import SentinelConfig

_CONFIG_FILENAME = "sentinel.yaml"


def find_config_file(start: Path) -> Path | None:
    """Search upward from *start* for a sentinel.yaml file.

    Returns the resolved path if found, or ``None``.
    """
    current = start.resolve()
    while True:
        candidate = current / _CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            return None
        current = parent


def load_config(path: Path | None = None) -> SentinelConfig:
    """Load and validate a :class:`SentinelConfig` from a YAML file.

    * If *path* is ``None``, returns the default configuration.
    * If the YAML file is empty, returns the default configuration.
    * Partial YAML is deep-merged with defaults via Pydantic model
      validation (missing keys get their defaults).
    * Extra top-level keys or invalid values raise
      :class:`pydantic.ValidationError`.
    """
    if path is None:
        return SentinelConfig()

    raw_text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text)

    if data is None:
        # Empty YAML document
        return SentinelConfig()

    if not isinstance(data, dict):
        msg = f"Expected a YAML mapping at top level, got {type(data).__name__}"
        raise TypeError(msg)

    return SentinelConfig.model_validate(data)
