"""Login, token refresh, logout and the signed-in user's own account (ADR 0005)."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, StringConstraints
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from diacare_gateway.auth.deps import CurrentUser, SessionDep, SettingsDep
from diacare_gateway.auth.passwords import DUMMY_HASH, verify_password
from diacare_gateway.auth.rate_limit import LoginRateLimiter
from diacare_gateway.auth.tokens import (
    create_access_token,
    hash_refresh_token,
    new_refresh_token,
)
from diacare_gateway.auth.users import EMAIL_TAKEN, create_user, find_user_by_email
from diacare_gateway.config import GatewaySettings
from diacare_gateway.db.models import AppUser, AuditEvent, Consent, RefreshToken
from diacare_gateway.routes import get_http_client
from diacare_shared.errors import AppError, ErrorCode
from diacare_shared.internal_auth import INTERNAL_TOKEN_HEADER, PATIENT_ID_HEADER
from diacare_shared.request_context import REQUEST_ID_HEADER, get_request_id

router = APIRouter(prefix="/api/v1", tags=["auth"])

INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
REGISTRATION_CLOSED = "REGISTRATION_CLOSED"

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
RegisterEmail = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_lower=True, min_length=3, max_length=254, pattern=_EMAIL_PATTERN
    ),
]
LoginEmail = Annotated[
    str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=254)
]
NewPassword = Annotated[str, StringConstraints(min_length=10, max_length=128)]
AnyPassword = Annotated[str, StringConstraints(min_length=1, max_length=128)]
Token = Annotated[str, StringConstraints(min_length=1, max_length=256)]


class RegisterRequest(BaseModel):
    email: RegisterEmail
    password: NewPassword
    display_name: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None
    ) = None
    consent_version: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    accept: Literal[True]


class RegisterResponse(BaseModel):
    user_id: uuid.UUID


class LoginRequest(BaseModel):
    email: LoginEmail
    password: AnyPassword


class RefreshRequest(BaseModel):
    refresh_token: Token


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserOut(BaseModel):
    user_id: uuid.UUID
    email: str
    display_name: str | None
    role: str
    created_at: datetime


def _aware(moment: datetime) -> datetime:
    """UTC-aware ``moment`` (SQLite returns naive values; they are UTC)."""
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _ip_hash(request: Request, settings: GatewaySettings) -> str:
    salted = f"{settings.jwt_secret or ''}:{_client_ip(request)}"
    return hashlib.sha256(salted.encode()).hexdigest()


def _audit(
    session: Session,
    event: str,
    user_id: uuid.UUID | None,
    request: Request,
    settings: GatewaySettings,
) -> None:
    session.add(
        AuditEvent(
            user_id=user_id,
            event=event,
            request_id=get_request_id(),
            ip_hash=_ip_hash(request, settings),
        )
    )


def _limiter(request: Request) -> LoginRateLimiter:
    limiter: LoginRateLimiter = request.app.state.rate_limiter
    return limiter


def _issue_tokens(
    session: Session, settings: GatewaySettings, user: AppUser, request: Request
) -> tuple[TokenPair, RefreshToken]:
    now = datetime.now(UTC)
    plain, hashed = new_refresh_token()
    row = RefreshToken(
        user_id=user.id,
        token_hash=hashed,
        issued_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_days),
        user_agent=(request.headers.get("user-agent") or "")[:255] or None,
    )
    session.add(row)
    session.flush()
    pair = TokenPair(
        access_token=create_access_token(settings, user.id, user.role, now),
        refresh_token=plain,
        expires_in=settings.access_token_minutes * 60,
    )
    return pair, row


def _invalid_refresh() -> AppError:
    return AppError(401, ErrorCode.UNAUTHORIZED, "Invalid or expired refresh token.")


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest, request: Request, session: SessionDep, settings: SettingsDep
) -> RegisterResponse:
    """Create a patient account. Closed unless REGISTRATION_ENABLED=true."""
    if not settings.registration_enabled:
        raise AppError(403, REGISTRATION_CLOSED, "Registration is closed.")
    try:
        user = create_user(
            session, email=body.email, password=body.password, display_name=body.display_name
        )
        session.add(Consent(user_id=user.id, consent_version=body.consent_version, scope="app_use"))
        _audit(session, "register", user.id, request, settings)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise AppError(409, EMAIL_TAKEN, "An account with this e-mail already exists.") from None
    return RegisterResponse(user_id=user.id)


@router.post("/auth/login")
def login(
    body: LoginRequest, request: Request, session: SessionDep, settings: SettingsDep
) -> TokenPair:
    limiter = _limiter(request)
    key = f"{body.email}|{_client_ip(request)}"
    if limiter.blocked(key):
        raise AppError(
            429,
            ErrorCode.TOO_MANY_ATTEMPTS,
            "Too many failed attempts. Try again later.",
            headers={"Retry-After": str(settings.login_window_minutes * 60)},
        )

    user = find_user_by_email(session, body.email)
    password_ok = verify_password(user.password_hash if user else DUMMY_HASH, body.password)
    if user is None or not password_ok or not user.is_active:
        limiter.record_failure(key)
        _audit(session, "login_failed", user.id if user else None, request, settings)
        session.commit()
        raise AppError(401, INVALID_CREDENTIALS, "Wrong e-mail or password.")

    limiter.reset(key)
    user.last_login_at = datetime.now(UTC)
    pair, _ = _issue_tokens(session, settings, user, request)
    _audit(session, "login_ok", user.id, request, settings)
    session.commit()
    return pair


@router.post("/auth/refresh")
def refresh(
    body: RefreshRequest, request: Request, session: SessionDep, settings: SettingsDep
) -> TokenPair:
    """Swap a refresh token for a new pair. Each refresh token works once."""
    now = datetime.now(UTC)
    row = session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(body.refresh_token)
        )
    )
    if row is None:
        raise _invalid_refresh()
    if row.revoked_at is not None:
        # A used token came back: assume it was stolen and end every session of this user.
        session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == row.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        _audit(session, "token_reuse", row.user_id, request, settings)
        session.commit()
        raise _invalid_refresh()
    user = session.get(AppUser, row.user_id)
    if _aware(row.expires_at) <= now or user is None or not user.is_active:
        raise _invalid_refresh()

    pair, new_row = _issue_tokens(session, settings, user, request)
    row.revoked_at = now
    row.replaced_by = new_row.id
    session.commit()
    return pair


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    body: RefreshRequest, request: Request, session: SessionDep, settings: SettingsDep
) -> Response:
    row = session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(body.refresh_token)
        )
    )
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        _audit(session, "logout", row.user_id, request, settings)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        created_at=_aware(user.created_at),
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    request: Request,
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> Response:
    """Delete the account and, through the services, every record of it (ADR 0006).

    New sessions are blocked first (the refresh tokens are revoked). If a service cannot delete
    its data the answer is 502 and the account stays as it is, so the same call can simply be
    repeated: each service's delete is idempotent.
    """
    user_id = user.id
    now = datetime.now(UTC)
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    session.commit()

    headers = {PATIENT_ID_HEADER: str(user_id)}
    if settings.internal_token:
        headers[INTERNAL_TOKEN_HEADER] = settings.internal_token
    request_id = get_request_id()
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id
    for name, base_url in settings.fanout_urls().items():
        url = f"{base_url.rstrip('/')}/internal/v1/patients/{user_id}"
        try:
            response = await client.delete(
                url, headers=headers, timeout=settings.default_timeout_seconds
            )
        except httpx.RequestError:
            response = None
        if response is None or response.status_code not in (200, 204):
            raise AppError(
                502,
                ErrorCode.UPSTREAM_UNAVAILABLE,
                f"Could not delete the data held by {name}. Nothing else was removed; try again.",
            )

    _audit(session, "account_deleted", None, request, settings)
    session.execute(delete(Consent).where(Consent.user_id == user_id))
    session.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    session.execute(delete(AppUser).where(AppUser.id == user_id))
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
