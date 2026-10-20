"""Trust between the gateway and the services (ADR 0005).

The gateway sends ``X-Patient-Id`` and ``X-Internal-Token``. A service believes the patient id
only when the token equals its own secret. Services never see passwords or login tokens.
"""

import hmac
import uuid
from collections.abc import Callable

from fastapi import Request

from diacare_shared.errors import AppError, ErrorCode

PATIENT_ID_HEADER = "X-Patient-Id"
INTERNAL_TOKEN_HEADER = "X-Internal-Token"


def _unauthorized(message: str) -> AppError:
    return AppError(401, ErrorCode.UNAUTHORIZED, message)


def check_internal_token(request: Request, expected: str | None) -> None:
    """Raise 401 unless the request carries the configured internal token."""
    if not expected:
        raise _unauthorized("The service has no internal token configured.")
    provided = request.headers.get(INTERNAL_TOKEN_HEADER, "")
    if not hmac.compare_digest(provided.encode(), expected.encode()):
        raise _unauthorized("Missing or wrong internal token.")


def read_patient_id(request: Request, expected_token: str | None) -> uuid.UUID:
    """The patient id sent by the gateway, after checking the internal token."""
    check_internal_token(request, expected_token)
    raw = request.headers.get(PATIENT_ID_HEADER, "")
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise _unauthorized("Missing or invalid patient id.") from None


def make_patient_id_dependency(
    get_expected_token: Callable[[Request], str | None],
) -> Callable[[Request], uuid.UUID]:
    """A FastAPI dependency returning the patient id; ``get_expected_token`` reads the secret."""

    def dependency(request: Request) -> uuid.UUID:
        return read_patient_id(request, get_expected_token(request))

    return dependency


def make_internal_token_dependency(
    get_expected_token: Callable[[Request], str | None],
) -> Callable[[Request], None]:
    """A FastAPI dependency that only checks the internal token (for ``/internal/...``)."""

    def dependency(request: Request) -> None:
        check_internal_token(request, get_expected_token(request))

    return dependency
