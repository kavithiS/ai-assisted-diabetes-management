"""Loads config.yaml once so every script reads the same settings."""

from pathlib import Path

import yaml

# ROOT is the project folder (one level above src/). Everything is relative to it,
# so the code works no matter which folder you run it from.
ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str = "config.yaml") -> dict:
    with open(ROOT / path, encoding="utf-8") as f:
        return yaml.safe_load(f)


CFG = load_config()


def abs_path(relative: str) -> Path:
    """Turn a path from config.yaml into a full path."""
    return ROOT / relative
