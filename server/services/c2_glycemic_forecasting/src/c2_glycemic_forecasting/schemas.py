"""Pydantic request/response schemas for C2 glucose forecasting."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class GlucoseForecastRequest(BaseModel):
    """Pre-meal glucose and nutrition inputs for a four-hour forecast."""

    model_config = ConfigDict(extra="forbid", strict=True)

    premeal_glucose: FiniteFloat = Field(
        gt=0,
        description="Current pre-meal glucose level in mg/dL.",
    )
    calories: FiniteFloat = Field(
        ge=0,
        description="Meal energy in kcal.",
    )
    carbs: FiniteFloat = Field(
        ge=0,
        description="Meal carbohydrates in grams.",
    )
    protein: FiniteFloat = Field(
        ge=0,
        description="Meal protein in grams.",
    )
    fat: FiniteFloat = Field(
        ge=0,
        description="Meal fat in grams.",
    )
    fiber: FiniteFloat = Field(
        ge=0,
        description="Meal fibre in grams.",
    )


class GlucoseForecastResponse(BaseModel):
    """Sixteen predicted glucose values over the next four hours."""

    model_config = ConfigDict(extra="forbid")

    predictions: list[FiniteFloat] = Field(
        min_length=16,
        max_length=16,
        description="Predicted glucose values at 15-minute intervals, in mg/dL.",
    )
    horizon_minutes: list[int] = Field(
        min_length=16,
        max_length=16,
        description="Prediction horizons: 15, 30, ..., 240 minutes.",
    )
    unit: Literal["mg/dL"] = "mg/dL"
    model_name: str
    model_version: str
    disclaimer: str


class DietaryRiskRequest(GlucoseForecastRequest):
    """Same inputs and validation rules as the forecast request."""


class TrajectoryFeaturesResponse(BaseModel):
    """Features of the predicted trajectory. Glucose in mg/dL, times in minutes."""

    model_config = ConfigDict(extra="forbid")

    predicted_peak_glucose: FiniteFloat = Field(description="Highest predicted value, mg/dL.")
    predicted_peak_minutes: int = Field(description="Minutes after the meal of the peak.")
    peak_change_from_premeal: FiniteFloat = Field(
        description="Predicted peak minus pre-meal glucose, mg/dL. Can be negative."
    )
    max_rise: FiniteFloat = Field(
        ge=0, description="Largest predicted increase from any earlier point, mg/dL."
    )
    max_rise_rate: FiniteFloat = Field(
        description="Steepest change between consecutive points, mg/dL per minute."
    )
    predicted_iauc: FiniteFloat = Field(
        ge=0, description="Incremental area above pre-meal glucose, mg/dL x min."
    )


class ResponseIndicator(BaseModel):
    """Research-defined post-meal hyperglycaemic response indicator (not a diagnosis)."""

    model_config = ConfigDict(extra="forbid")

    name: Literal["above_180_within_4h"] = "above_180_within_4h"
    status: Literal["available", "unavailable"]
    estimated_above_180: bool | None = Field(
        description="Classifier estimate; null when the status is unavailable."
    )
    definition: str
    evaluation_note: str | None
    model_name: str | None
    model_version: str | None


class DietaryRiskResponse(BaseModel):
    """GRU forecast, its trajectory features and the response indicator for one meal."""

    model_config = ConfigDict(extra="forbid")

    predictions: list[FiniteFloat] = Field(min_length=16, max_length=16)
    horizon_minutes: list[int] = Field(min_length=16, max_length=16)
    unit: Literal["mg/dL"] = "mg/dL"
    trajectory_features: TrajectoryFeaturesResponse
    response_indicator: ResponseIndicator
    forecast_model_name: str
    forecast_model_version: str
    disclaimer: str
