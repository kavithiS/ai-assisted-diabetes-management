"""Gateway-only endpoints (``/internal/...``). They check the internal token, nothing else."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Response, status

from c1_food_nutrition.api.deps import SessionDep, require_internal_token
from c1_food_nutrition.services.meal_history import MealHistoryService

router = APIRouter(
    prefix="/internal/v1", tags=["internal"], dependencies=[Depends(require_internal_token)]
)


@router.delete(
    "/patients/{patient_id}",
    summary="Delete everything stored for one patient",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_patient(session: SessionDep, patient_id: Annotated[UUID, Path()]) -> Response:
    """Idempotent: 204 whether or not the patient had any data."""
    MealHistoryService(session).delete_patient(patient_id)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
