"""Pydantic request/response schemas for C3.

They follow docs/contract_proposal.md: `patient_risk_profile` 0.2 (client -> C3) and
`risk_assessment` 0.2 (C3 -> client). 0.1 requests (no lifestyle answers) still work.
Outputs are estimates and predictions, never diagnoses.
Ranges are checked by the model layer, which answers `invalid_input`, so the API only
rejects wrong types or unknown fields (HTTP 422).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["ok", "insufficient_data", "invalid_input"]
Band = Literal["Low", "Moderate", "High"]
FeatureSet = Literal["with_glucose", "without_glucose"]
Direction = Literal["increases risk", "decreases risk"]
YesNo = Literal[0, 1]


class PatientRiskProfile(BaseModel):
    """What the client sends. Every field is optional so missing data can be reported."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1", "0.2"] = "0.2"
    age: float | None = Field(default=None, description="Age in years (18-100). Critical.")
    sex_male: int | None = Field(default=None, description="1 = male, 0 = female.")
    bmi: float | None = Field(default=None, description="Body mass index, kg/m2 (12-70). Critical.")
    systolic_bp: float | None = Field(default=None, description="mmHg (70-260). Critical.")
    diastolic_bp: float | None = Field(default=None, description="mmHg (40-150). Critical.")
    pulse_rate: float | None = Field(default=None, description="Resting pulse, beats/min (35-200).")
    glucose_mmol: float | None = Field(
        default=None,
        description="Blood glucose, mmol/L (1.5-40). When given, the glucose model is used.",
    )
    family_history_diabetes: int | None = Field(default=None, description="1 = yes, 0 = no.")
    family_history_hypertension: int | None = Field(default=None, description="1 = yes, 0 = no.")
    hypertensive: int | None = Field(default=None, description="Diagnosed high BP, 1 / 0.")
    cardiovascular_disease: int | None = Field(default=None, description="1 = yes, 0 = no.")
    stroke: int | None = Field(default=None, description="1 = yes, 0 = no.")

    # TAF task 1 lifestyle / clinical answers (0.2). They feed the DHS and the
    # recommendations only; the v1 risk model does not use them (no real training data).
    physical_activity: Literal["low", "moderate", "high"] | None = None
    smoker: YesNo | None = None
    medication_adherence: Literal["poor", "fair", "good"] | None = None
    cholesterol_level: Literal["normal", "borderline_high", "high"] | None = None
    kidney_disease: YesNo | None = Field(
        default=None, description="Diagnosed kidney condition. DHS only, never a model input."
    )
    liver_disease: YesNo | None = Field(
        default=None, description="Diagnosed liver condition. DHS only, never a model input."
    )
    weight_change_kg: float | None = Field(
        default=None, ge=-30, le=30, description="Weight now minus 3 months ago, kg."
    )


class ShapFactor(BaseModel):
    feature: str
    readable: str
    factor_type: str
    value: float
    shap: float
    direction: Direction


class LimeFactor(BaseModel):
    rule: str
    feature: str
    readable: str
    factor_type: str
    value: float
    weight: float
    direction: Direction


class Agreement(BaseModel):
    shap_top: list[str]
    lime_top: list[str]
    shared: list[str]
    overlap_ratio: float
    meets_target: bool


class Explanation(BaseModel):
    shap: list[ShapFactor]
    lime: list[LimeFactor]
    lime_fidelity: float
    agreement: Agreement
    explanation_quality: str
    explanation_text: str


class DhsItem(BaseModel):
    factor: str
    label: str
    value: str | int | float
    item_score: float = Field(description="1 favourable, 0.5 in between, 0 unfavourable.")
    group: Literal["behaviour", "clinical marker"]


class DhsComponents(BaseModel):
    stable: float
    behaviour: float | None
    glycemic: float | None = Field(description="From C2 (PP2); null for now.")
    uncertainty: float


class Dhs(BaseModel):
    """Diabetic Health Score, 0-100, higher is better. PROVISIONAL weights."""

    score: float
    today_score: float
    previous_score: float | None = None
    components: DhsComponents
    items: list[DhsItem]
    provisional: bool
    note: str


class Recommendation(BaseModel):
    id: str
    factor: str
    title: str
    trigger: str
    raised_estimate: bool
    window: str
    action: str
    seek_care: str | None = None
    current: str | None = None
    target: str | None = None
    review_status: str


class DebugInfo(BaseModel):
    """Researcher-only. Returned only in research mode and when `?debug=true`."""

    risk_probability: float
    risk_percent: float
    thresholds: dict[str, float]


class RiskAssessment(BaseModel):
    """What C3 returns. Fields that do not apply to a status are omitted."""

    status: Status
    disclaimer: str
    risk_category: Band | None = None
    referral: str | None = None
    feature_set: FeatureSet | None = None
    model_used: str | None = None
    model_version: str | None = None
    data_complete: bool | None = None
    imputed_fields: list[str] | None = None
    missing_critical_fields: list[str] | None = None
    problems: list[str] | None = None
    explanation: Explanation | None = None
    dhs: Dhs | None = None
    recommendations: list[Recommendation] | None = None
    saved: bool | None = Field(
        default=None,
        description="True when stored in the c3 database. False: storage failed (best-effort, "
        "the result is still valid). Omitted when no X-Device-Id was sent.",
    )
    debug: DebugInfo | None = None


DatabaseState = Literal["ok", "unreachable", "not_set_up", "off"]


class ModelStatus(BaseModel):
    model_loaded: bool
    models: dict[str, str]
    detail: str | None = None
    database: DatabaseState | None = Field(
        default=None,
        description="ok; unreachable (Postgres down); not_set_up (run alembic upgrade head); "
        "off (C3_PERSISTENCE=false).",
    )


class HistoryItem(BaseModel):
    """One past assessment of this device (FR13). No answers are returned."""

    id: str
    assessed_at: datetime
    status: Status
    risk_category: Band | None = None
    model_version: str | None = None
    schema_version: str
    dhs: float | None = None


class History(BaseModel):
    items: list[HistoryItem]


class DeletedRecords(BaseModel):
    """FR16: how many assessments were removed. The action is written to the audit log."""

    deleted_assessments: int
