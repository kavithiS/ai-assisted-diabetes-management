"""C2 API routes. Placeholders until the owner implements them."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/v1/glucose", tags=["glucose"])


@router.post("/forecast", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def forecast_glucose() -> None:
    """Placeholder. Request and response follow the planned `glucose_forecast` contract."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
