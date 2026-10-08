"""C3 API routes. Placeholders until the owner implements them."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/v1/risk", tags=["risk"])


@router.post("/assess", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def assess_risk() -> None:
    """Placeholder. Request and response follow the planned `risk_assessment` contract."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
