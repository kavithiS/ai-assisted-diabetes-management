"""C4 API routes. Placeholders until the owner implements them."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/v1/foot", tags=["foot"])


@router.post("/analyze", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def analyze_foot() -> None:
    """Placeholder. Request and response follow the planned `foot_analysis` contract."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
