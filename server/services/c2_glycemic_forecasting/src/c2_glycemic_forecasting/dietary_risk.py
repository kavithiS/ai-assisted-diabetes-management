"""Inference for the C2 XGBoost post-meal response classifier.

The classifier estimates the research-defined indicator `above_180_within_4h`: whether at least
one CGM reading from +15 to +240 minutes after the meal will be above 180 mg/dL. It is not a
clinically validated risk category. Its artefacts come from training/train_dietary_risk_xgb.py.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import xgboost as xgb

from c2_glycemic_forecasting.trajectory_features import FEATURE_NAMES

DEFAULT_MODEL_DIR = (
    Path.home() / "Desktop" / "CGMacros_C2_processed_premeal_fix" / "results_dietary_risk_xgb"
)
MODEL_FILE = "dietary_risk_xgb.json"
METADATA_FILE = "dietary_risk_xgb_metadata.json"
LABEL_NAME = "above_180_within_4h"


class ClassifierUnavailableError(Exception):
    """The classifier artefacts are missing, unreadable or inconsistent."""


@dataclass(frozen=True)
class DietaryRiskClassifier:
    booster: xgb.Booster
    threshold: float
    model_name: str
    model_version: str
    label_definition: str
    evaluation_note: str

    def estimate_above_threshold(self, features: Mapping[str, float]) -> bool:
        """Return True when the classifier estimates a reading above 180 mg/dL."""
        if tuple(features) != FEATURE_NAMES:
            raise ValueError("Features must be given in FEATURE_NAMES order.")
        row = np.array([[features[name] for name in FEATURE_NAMES]], dtype=np.float64)
        matrix = xgb.DMatrix(row, feature_names=list(FEATURE_NAMES), missing=np.nan)
        score = float(self.booster.predict(matrix)[0])
        if not math.isfinite(score):
            raise ValueError("The classifier produced a non-finite score.")
        return score >= self.threshold


def _model_dir() -> Path:
    """Allow deployment to override the local artefact location."""
    return Path(os.environ.get("C2_DIETARY_RISK_MODEL_DIR", str(DEFAULT_MODEL_DIR)))


def _require(metadata: Mapping[str, Any], key: str, kind: type) -> Any:
    value = metadata.get(key)
    if not isinstance(value, kind):
        raise ClassifierUnavailableError(
            f"Classifier metadata field {key!r} is missing or invalid."
        )
    return value


@lru_cache(maxsize=1)
def load_classifier() -> DietaryRiskClassifier:
    """Load and check the classifier. Raises ClassifierUnavailableError on any problem."""
    directory = _model_dir()
    model_path = directory / MODEL_FILE
    metadata_path = directory / METADATA_FILE
    try:
        model_bytes = model_path.read_bytes()
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ClassifierUnavailableError(f"Cannot read classifier files in {directory}.") from error
    if not isinstance(metadata, dict):
        raise ClassifierUnavailableError("Classifier metadata must be a JSON object.")

    if hashlib.sha256(model_bytes).hexdigest() != _require(metadata, "model_sha256", str):
        raise ClassifierUnavailableError("Classifier model file does not match its metadata.")
    if tuple(_require(metadata, "feature_names", list)) != FEATURE_NAMES:
        raise ClassifierUnavailableError("Classifier features do not match this service.")
    if _require(metadata, "label_name", str) != LABEL_NAME:
        raise ClassifierUnavailableError("Classifier was trained for a different label.")
    threshold = _require(metadata, "decision_threshold", float)
    if not 0.0 < threshold < 1.0:
        raise ClassifierUnavailableError("Classifier decision threshold must be in (0, 1).")

    booster = xgb.Booster()
    try:
        booster.load_model(bytearray(model_bytes))
    except xgb.core.XGBoostError as error:
        raise ClassifierUnavailableError("Classifier model file is invalid.") from error
    if booster.num_features() != len(FEATURE_NAMES):
        raise ClassifierUnavailableError("Classifier model has an unexpected number of features.")

    return DietaryRiskClassifier(
        booster=booster,
        threshold=threshold,
        model_name=_require(metadata, "model_name", str),
        model_version=_require(metadata, "model_version", str),
        label_definition=_require(metadata, "label_definition", str),
        evaluation_note=_require(metadata, "evaluation_note", str),
    )
