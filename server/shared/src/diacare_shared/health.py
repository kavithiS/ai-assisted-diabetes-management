"""Standard `GET /health` endpoint for services."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str


def create_health_router(service_name: str) -> APIRouter:
    """Return a router exposing `GET /health` for the given service package name."""
    router = APIRouter(tags=["health"])

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service=service_name)

    return router
