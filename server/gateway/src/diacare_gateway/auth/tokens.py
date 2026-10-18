"""Access tokens (JWT) and refresh tokens (random, stored only as a SHA-256 hash)."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from diacare_gateway.config import GatewaySettings
from diacare_shared.errors import AppError, ErrorCode

ACCESS_TOKEN_TYPE = "access"


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: uuid.UUID
    role: str


def _secret(settings: GatewaySettings) -> str:
    if not settings.jwt_secret:
        raise AppError(503, ErrorCode.SERVICE_UNAVAILABLE, "Login is not configured (JWT_SECRET).")
    return settings.jwt_secret


def create_access_token(
    settings: GatewaySettings, user_id: uuid.UUID, role: str, now: datetime | None = None
) -> str:
    issued = now or datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "role": role,
        "iat": issued,
        "exp": issued + timedelta(minutes=settings.access_token_minutes),
        "jti": uuid.uuid4().hex,
        "typ": ACCESS_TOKEN_TYPE,
    }
    return jwt.encode(claims, _secret(settings), algorithm=settings.jwt_algorithm)


def decode_access_token(settings: GatewaySettings, token: str) -> AccessClaims:
    """Verify signature, expiry and type; any problem is the same 401."""
    try:
        claims = jwt.decode(
            token,
            _secret(settings),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat", "typ"]},
        )
        if claims["typ"] != ACCESS_TOKEN_TYPE:
            raise ValueError("not an access token")
        return AccessClaims(user_id=uuid.UUID(claims["sub"]), role=str(claims.get("role", "")))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise AppError(
            401,
            ErrorCode.UNAUTHORIZED,
            "Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_refresh_token() -> tuple[str, str]:
    """(token to give the client, hash to store)."""
    token = secrets.token_urlsafe(32)
    return token, hash_refresh_token(token)
