"""Configuration file discovery and loading for mastiff."""

from __future__ import annotations

from pathlib import Path

import yaml

from mastiff.config.schema import MastiffConfig

_CONFIG_FILENAME = "mastiff.yaml"


def find_config_file(start: Path) -> Path | None:
    """Search upward from *start* for a mastiff.yaml file.

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


def load_config(path: Path | None = None) -> MastiffConfig:
    """Load and validate a :class:`MastiffConfig` from a YAML file.

    * If *path* is ``None``, returns the default configuration.
    * If the YAML file is empty, returns the default configuration.
    * Partial YAML is deep-merged with defaults via Pydantic model
      validation (missing keys get their defaults).
    * Extra top-level keys or invalid values raise
      :class:`pydantic.ValidationError`.
    """
    if path is None:
        return MastiffConfig()

    raw_text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text)

    if data is None:
        # Empty YAML document
        return MastiffConfig()

    if not isinstance(data, dict):
        msg = f"Expected a YAML mapping at top level, got {type(data).__name__}"
        raise TypeError(msg)

    return MastiffConfig.model_validate(data)
