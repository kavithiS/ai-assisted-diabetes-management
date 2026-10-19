"""DHS and recommendation tests (TAF task 4, proposal 3.4.4 / 3.4.5, FR10, FR11, NFR11).

The proposal's DHS checks: range, monotonicity, reproducibility, sensitivity to modifiable
factors, resistance to one noisy observation, behaviour under missing data, and template
triggering.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from c3_risk_xai.db.repository import InMemoryAssessmentStore
from c3_risk_xai.ml import dhs, recommend
from c3_risk_xai.ml.predict import EXAMPLE_PATIENT
from c3_risk_xai.schemas import PatientRiskProfile
from c3_risk_xai.services import risk_service

HEALTHY = {
    "physical_activity": "high",
    "smoker": 0,
    "medication_adherence": "good",
    "weight_change_kg": 0.0,
    "cholesterol_level": "normal",
    "kidney_disease": 0,
    "liver_disease": 0,
}
UNHEALTHY = {
    "physical_activity": "low",
    "smoker": 1,
    "medication_adherence": "poor",
    "weight_change_kg": 6.0,
    "cholesterol_level": "high",
    "kidney_disease": 1,
    "liver_disease": 1,
}
DEVICE = "0123456789abcdef0123456789abcdef"


def score(answers: dict[str, Any], risk: float = 0.3, previous: float | None = None) -> float:
    return float(dhs.compute(answers, risk, previous)["score"])


def test_score_is_always_between_0_and_100() -> None:
    for answers in (HEALTHY, UNHEALTHY, {}):
        for risk in (0.0, 0.5, 1.0):
            assert 0.0 <= score(answers, risk) <= 100.0


def test_monotonic_in_estimated_risk_and_in_habits() -> None:
    assert score(HEALTHY, 0.1) > score(HEALTHY, 0.6)
    assert score(HEALTHY) > score(UNHEALTHY)


def test_same_input_gives_the_same_score() -> None:
    assert dhs.compute(UNHEALTHY, 0.42) == dhs.compute(UNHEALTHY, 0.42)


@pytest.mark.parametrize(
    ("factor", "better", "worse"),
    [
        ("physical_activity", "high", "low"),
        ("smoker", 0, 1),
        ("medication_adherence", "good", "poor"),
        ("weight_change_kg", 0.5, 8.0),
        ("cholesterol_level", "normal", "high"),
    ],
)
def test_each_modifiable_factor_moves_the_score(factor: str, better: Any, worse: Any) -> None:
    assert score({**UNHEALTHY, factor: better}) > score({**UNHEALTHY, factor: worse})


def test_one_noisy_answer_moves_the_smoothed_score_only_half_way() -> None:
    steady = score(HEALTHY)
    noisy_today = score(UNHEALTHY)
    smoothed = score(UNHEALTHY, previous=steady)
    assert noisy_today < smoothed < steady
    assert smoothed == pytest.approx((steady + noisy_today) / 2, abs=0.11)


def test_missing_answers_lower_the_score_and_are_left_out() -> None:
    full = dhs.compute(HEALTHY, 0.3)
    partial = dhs.compute({"physical_activity": "high"}, 0.3)
    assert partial["components"]["uncertainty"] > full["components"]["uncertainty"]
    assert partial["score"] < full["score"]
    assert [i["factor"] for i in partial["items"]] == ["physical_activity"]
    assert dhs.compute({}, 0.3)["components"]["behaviour"] is None


def test_dhs_is_marked_provisional() -> None:
    out = dhs.compute(HEALTHY, 0.3)
    assert out["provisional"] is True
    assert "pending clinician review" in out["note"]
    assert out["components"]["glycemic"] is None  # C2 not connected yet


def test_templates_trigger_only_for_their_answers() -> None:
    ids = {r["id"] for r in recommend.build(UNHEALTHY, shap_rows=[])}
    assert {"activity", "smoking", "adherence"} <= ids
    assert recommend.build(HEALTHY, shap_rows=[]) == []


def test_recommendations_are_safe() -> None:
    every_rule = {**UNHEALTHY}
    rows = [{"feature": f, "shap": 0.1} for f in ("bmi", "systolic_bp", "glucose_mmol", "age")]
    items = [*recommend.build(every_rule, rows), *recommend.build({"weight_change_kg": -6.0}, rows)]
    for item in items:
        text = f"{item['title']} {item['action']}".lower()
        assert (
            "stop taking" not in text
            and "dose" not in text
            and "increase your medicine" not in text
        )
        assert item["review_status"].startswith("provisional")
        assert item["factor"] not in {"age", "sex_male", "family_history_diabetes"}  # immutable
    adherence = next(i for i in recommend.build(UNHEALTHY, []) if i["id"] == "adherence")
    assert "do not change or stop any medicine yourself" in adherence["action"].lower()
    assert adherence["seek_care"]


def test_factors_that_raised_the_estimate_come_first() -> None:
    items = recommend.build({"physical_activity": "low"}, [{"feature": "bmi", "shap": 0.2}])
    assert items[0]["id"] == "bmi" and items[0]["raised_estimate"] is True


@pytest.fixture
def service(fake_models: Path) -> Iterator[InMemoryAssessmentStore]:
    assert risk_service.load_models().model_loaded
    store = InMemoryAssessmentStore()
    risk_service.use_store(store)
    yield store
    risk_service.use_store(None, "off")


@pytest.mark.slow
def test_lifestyle_answers_reach_the_dhs_but_never_the_model(
    service: InMemoryAssessmentStore,
) -> None:
    plain = risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT))
    extended = risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT, **UNHEALTHY))
    healthier = risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT, **HEALTHY))

    # Same model answer with or without lifestyle answers: they never reach the model.
    assert extended.risk_category == plain.risk_category == healthier.risk_category
    assert extended.explanation is not None and plain.explanation is not None
    assert [f.shap for f in extended.explanation.shap] == [f.shap for f in plain.explanation.shap]
    # ...but they do move the DHS.
    assert extended.dhs is not None and healthier.dhs is not None
    assert extended.dhs.score < healthier.dhs.score
    assert extended.recommendations
    assert extended.recommendations[0].review_status.startswith("provisional")


@pytest.mark.slow
def test_dhs_adapts_to_the_previous_score_of_the_same_device(
    service: InMemoryAssessmentStore,
) -> None:
    first = risk_service.assess(PatientRiskProfile(**EXAMPLE_PATIENT, **HEALTHY), device_id=DEVICE)
    second = risk_service.assess(
        PatientRiskProfile(**EXAMPLE_PATIENT, **UNHEALTHY), device_id=DEVICE
    )
    assert first.dhs is not None and second.dhs is not None
    assert second.dhs.previous_score == first.dhs.score
    assert second.dhs.today_score < second.dhs.score < first.dhs.score
    assert service.rows[-1][1].dhs == second.dhs.score


def test_v1_request_still_works_and_bad_lifestyle_values_are_rejected() -> None:
    assert PatientRiskProfile(schema_version="0.1", age=50).schema_version == "0.1"
    with pytest.raises(ValueError):
        PatientRiskProfile(physical_activity="sometimes")
    with pytest.raises(ValueError):
        PatientRiskProfile(weight_change_kg=80)
