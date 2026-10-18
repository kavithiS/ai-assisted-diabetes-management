"""Who is calling? Reads the Bearer token and loads the user (ADR 0005)."""

import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from diacare_gateway.auth.tokens import decode_access_token
from diacare_gateway.config import GatewaySettings, get_settings
from diacare_gateway.db.models import AppUser
from diacare_shared.errors import AppError, ErrorCode

SettingsDep = Annotated[GatewaySettings, Depends(get_settings)]


def _factory(request: Request) -> sessionmaker[Session]:
    factory: sessionmaker[Session] | None = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise AppError(
            503, ErrorCode.SERVICE_UNAVAILABLE, "Login is not configured (GATEWAY_DATABASE_URL)."
        )
    return factory


def get_db_session(request: Request) -> Iterator[Session]:
    """One `core` database session per request; the endpoint commits what it wants to keep."""
    with _factory(request)() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db_session)]


def _unauthorized(message: str) -> AppError:
    return AppError(401, ErrorCode.UNAUTHORIZED, message, headers={"WWW-Authenticate": "Bearer"})


def _user_from_token(request: Request, session: Session, settings: GatewaySettings) -> AppUser:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized("Missing bearer token.")
    claims = decode_access_token(settings, token.strip())
    user = session.get(AppUser, claims.user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Invalid or expired token.")
    return user


def current_user(request: Request, session: SessionDep, settings: SettingsDep) -> AppUser:
    """The signed-in user. Always needs a real token (used by /me)."""
    return _user_from_token(request, session, settings)


def current_patient_id(request: Request, settings: SettingsDep) -> uuid.UUID:
    """The patient id to send to the services.

    With ``AUTH_REQUIRED=false`` this is the fixed demo patient (the app has no login yet).
    """
    if not settings.auth_required:
        if settings.demo_patient_id is None:
            raise AppError(
                503,
                ErrorCode.SERVICE_UNAVAILABLE,
                "AUTH_REQUIRED is false but DEMO_PATIENT_ID is not set.",
            )
        return settings.demo_patient_id
    with _factory(request)() as session:
        return _user_from_token(request, session, settings).id


CurrentUser = Annotated[AppUser, Depends(current_user)]
PatientId = Annotated[uuid.UUID, Depends(current_patient_id)]
