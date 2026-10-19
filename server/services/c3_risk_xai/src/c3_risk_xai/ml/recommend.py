"""Recommendations: a fixed rule base of message templates (proposal 3.4.5, FR11, NFR11).

- Only MODIFIABLE factors get advice. Age, sex and family history give context only.
- Never advise starting, stopping or changing medicine; refer to the doctor instead.
- Each message names its trigger, the direction (raised the estimate or not), the
  observation window, one low-risk self-management action, and a "seek care" line when
  medication, abnormal results or concerning patterns are involved.
- Every template is PROVISIONAL until a clinician has reviewed the wording (TAF task 5).
- Factors that SHAP says raised this person's estimate come first. No free-text generation.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

REVIEW_STATUS = "provisional - pending clinician review"
MAX_ITEMS = 4
ANSWERS_WINDOW = "your latest answers"


@dataclass(frozen=True)
class Template:
    id: str
    factor: str  # answer or model feature it is about
    title: str
    applies: Callable[[dict[str, Any], set[str]], bool]
    trigger: str
    action: str
    window: str = ANSWERS_WINDOW
    seek_care: str | None = None
    current: Callable[[dict[str, Any]], str | None] = lambda _: None
    target: str | None = None


def _answer(field: str, *values: Any) -> Callable[[dict[str, Any], set[str]], bool]:
    return lambda answers, _raised: answers.get(field) in values


def _raised(feature: str) -> Callable[[dict[str, Any], set[str]], bool]:
    return lambda _answers, raised: feature in raised


def _weight(direction: int) -> Callable[[dict[str, Any], set[str]], bool]:
    def check(answers: dict[str, Any], _raised: set[str]) -> bool:
        change = answers.get("weight_change_kg")
        return change is not None and direction * float(change) > 2.0

    return check


RULES: tuple[Template, ...] = (
    Template(
        id="activity",
        factor="physical_activity",
        title="Increase physical activity",
        applies=_answer("physical_activity", "low", "moderate"),
        trigger="Physical activity answered as low or moderate",
        action="Build up step by step to at least 150 minutes of moderate activity a week, "
        "for example brisk walking, if your doctor agrees.",
        current=lambda a: f"{str(a['physical_activity']).capitalize()} activity",
        target="150 min of moderate activity per week (WHO guideline)",
    ),
    Template(
        id="smoking",
        factor="smoker",
        title="Stop smoking",
        applies=_answer("smoker", 1),
        trigger="Smoking answered as yes",
        action="Set a quit date and ask a friend or family member to support you.",
        seek_care="Your clinic or doctor can offer support to quit.",
    ),
    Template(
        id="adherence",
        factor="medication_adherence",
        title="Keep taking your medicines as prescribed",
        applies=_answer("medication_adherence", "poor", "fair"),
        trigger="Medication adherence answered as poor or fair",
        action="Use a daily reminder or a pill box. Do not change or stop any medicine yourself.",
        seek_care="If taking your medicines is difficult, talk to your doctor or pharmacist.",
    ),
    Template(
        id="cholesterol",
        factor="cholesterol_level",
        title="Review your cholesterol with your doctor",
        applies=_answer("cholesterol_level", "borderline_high", "high"),
        trigger="Cholesterol answered as borderline high or high",
        action="Choose fewer fried and fatty foods and more vegetables and whole grains.",
        seek_care="Discuss your cholesterol result with your doctor.",
    ),
    Template(
        id="weight_gain",
        factor="weight_change_kg",
        title="Monitor your body weight weekly",
        applies=_weight(+1),
        trigger="Weight went up more than 2 kg in 3 months",
        action="Weigh yourself once a week; small, steady changes in meals and activity help.",
        window="the last 3 months",
    ),
    Template(
        id="weight_loss",
        factor="weight_change_kg",
        title="Tell your doctor about weight loss",
        applies=_weight(-1),
        trigger="Weight went down more than 2 kg in 3 months",
        action="Keep a note of your weight once a week.",
        window="the last 3 months",
        seek_care="Weight loss you did not plan should be checked by a doctor.",
    ),
    Template(
        id="kidney",
        factor="kidney_disease",
        title="Keep your kidney check-ups",
        applies=_answer("kidney_disease", 1),
        trigger="Kidney condition answered as yes",
        action="Keep your regular appointments and urine and blood tests.",
        seek_care="Ask your doctor before using painkillers regularly.",
    ),
    Template(
        id="liver",
        factor="liver_disease",
        title="Keep your liver check-ups",
        applies=_answer("liver_disease", 1),
        trigger="Liver condition answered as yes",
        action="Keep your regular appointments and avoid alcohol.",
        seek_care="Follow your doctor's plan for your liver condition.",
    ),
    Template(
        id="bmi",
        factor="bmi",
        title="Work towards a healthy body weight",
        applies=_raised("bmi"),
        trigger="Body mass index raised the model's estimate",
        action="Aim for regular meals with smaller portions of rice and more vegetables.",
    ),
    Template(
        id="blood_pressure",
        factor="systolic_bp",
        title="Check your blood pressure regularly",
        applies=lambda _a, raised: bool({"systolic_bp", "diastolic_bp"} & raised),
        trigger="Blood pressure raised the model's estimate",
        action="Use less salt and keep a record of your blood pressure readings.",
        seek_care="Follow your doctor's advice about blood pressure.",
    ),
    Template(
        id="glucose",
        factor="glucose_mmol",
        title="Discuss your blood glucose result",
        applies=_raised("glucose_mmol"),
        trigger="Blood glucose raised the model's estimate",
        action="Keep a record of your glucose results to show your doctor.",
        seek_care="Discuss your glucose result with your doctor or diabetes clinic.",
    ),
)


def build(answers: dict[str, Any], shap_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Messages for this patient, those linked to risk-raising model factors first."""
    raised = {r["feature"] for r in shap_rows if r["shap"] > 0}
    items = []
    for rule in RULES:
        if not rule.applies(answers, raised):
            continue
        items.append(
            {
                "id": rule.id,
                "factor": rule.factor,
                "title": rule.title,
                "trigger": rule.trigger,
                "raised_estimate": rule.factor in raised
                or (rule.id == "blood_pressure" and bool(raised & {"diastolic_bp"})),
                "window": rule.window,
                "action": rule.action,
                "seek_care": rule.seek_care,
                "current": rule.current(answers),
                "target": rule.target,
                "review_status": REVIEW_STATUS,
            }
        )
    items.sort(key=lambda item: not item["raised_estimate"])  # stable sort keeps rule order
    return items[:MAX_ITEMS]
