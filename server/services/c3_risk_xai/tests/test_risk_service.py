"""Service layer tests: risk_service must pass the model's answer through unchanged.

Uses the stand-in models from conftest.py, so no dataset or trained model is needed.
"""

from pathlib import Path
from typing import Any

import pytest

from c3_risk_xai.ml import predict
from c3_risk_xai.ml.config import CFG
from c3_risk_xai.ml.explain import explain_patient
from c3_risk_xai.ml.predict import EXAMPLE_PATIENT, LOW_RISK_PATIENT
from c3_risk_xai.schemas import PatientRiskProfile
from c3_risk_xai.services import risk_service


@pytest.fixture
def loaded(fake_models: Path) -> None:
    assert risk_service.load_models().model_loaded


@pytest.mark.slow
@pytest.mark.parametrize("preset", [EXAMPLE_PATIENT, LOW_RISK_PATIENT])
def test_presets_equal_calling_ml_directly(loaded: None, preset: dict[str, Any]) -> None:
    out = risk_service.assess(PatientRiskProfile(**preset), include_debug=True)
    direct = explain_patient(dict(preset))
    expected = direct["prediction"]

    assert out.status == "ok"
    assert out.risk_category == expected["risk_category"]
    assert out.debug is not None
    assert out.debug.risk_probability == expected["risk_probability"]
    assert out.debug.thresholds == expected["thresholds"]
    assert out.explanation is not None
    assert out.explanation.explanation_text == direct["explanation_text"]
    assert [f.feature for f in out.explanation.shap] == [r["feature"] for r in direct["shap"]]


@pytest.mark.slow
def test_debug_is_hidden_by_default(loaded: None) -> None:
    out = risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT))
    assert out.debug is None


@pytest.mark.parametrize("field", CFG["critical_fields"])
def test_missing_critical_field_gives_insufficient_data(loaded: None, field: str) -> None:
    profile = {k: v for k, v in EXAMPLE_PATIENT.items() if k != field}
    out = risk_service.assess(PatientRiskProfile(**profile))

    assert out.status == "insufficient_data"
    assert out.risk_category is None
    assert out.explanation is None
    assert out.missing_critical_fields == [field]


def test_out_of_range_values_give_invalid_input(loaded: None) -> None:
    out = risk_service.assess(PatientRiskProfile(**dict(EXAMPLE_PATIENT, bmi=500, stroke=3)))

    assert out.status == "invalid_input"
    assert out.risk_category is None
    assert out.problems is not None
    assert any("bmi" in p for p in out.problems)
    assert any("stroke" in p for p in out.problems)


@pytest.mark.slow
def test_glucose_presence_picks_the_model(loaded: None) -> None:
    with_glucose = risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT))
    no_glucose = risk_service.assess(PatientRiskProfile(**dict(EXAMPLE_PATIENT, glucose_mmol=None)))

    assert with_glucose.feature_set == "with_glucose"
    assert no_glucose.feature_set == "without_glucose"


def test_missing_bundles_report_not_loaded(
    fake_models: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(predict, "MODEL_DIR", tmp_path)
    status = risk_service.load_models()

    assert status.model_loaded is False
    with pytest.raises(risk_service.ModelsNotLoadedError):
        risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT))
    predict.load_bundle.cache_clear()
