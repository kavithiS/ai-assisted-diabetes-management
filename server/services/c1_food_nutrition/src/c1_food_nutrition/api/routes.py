"""C1 API routes. Placeholders until the owner implements them."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/v1/meals", tags=["meals"])


@router.post("/analyze", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def analyze_meal() -> None:
    """Placeholder. Request and response follow the planned `meal_nutrition` contract."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
