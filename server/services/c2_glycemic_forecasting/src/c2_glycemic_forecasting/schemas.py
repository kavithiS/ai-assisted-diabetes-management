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
