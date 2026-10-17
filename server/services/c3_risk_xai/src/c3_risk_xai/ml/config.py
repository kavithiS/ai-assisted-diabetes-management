# mypy: ignore-errors
# Older ML code, not fully typed yet. Remove these two lines once it is (docs/ci_pr_note.md).
"""Loads config.yaml once so every script reads the same settings."""

from pathlib import Path
from typing import Any

import yaml

# This file is server/services/c3_risk_xai/src/c3_risk_xai/ml/config.py.
# SERVICE_ROOT holds config.yaml and docs/; REPO_ROOT holds data/c3/ (gitignored).
# Both are found from this file, so the code works from any working directory.
SERVICE_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = Path(__file__).resolve().parents[6]


def load_config(path: str = "config.yaml") -> dict[str, Any]:
    with open(SERVICE_ROOT / path, encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f)
    return config


CFG = load_config()


def abs_path(relative: str) -> Path:
    """Turn a repo-root-relative path from config.yaml into a full path."""
    return REPO_ROOT / relative
