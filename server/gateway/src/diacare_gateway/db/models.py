"""Tables of the `core` schema: users, login tokens, consent and audit (ADR 0005, 0006).

No health data lives here. Passwords are stored only as Argon2 hashes and refresh tokens only
as SHA-256 hashes.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from diacare_gateway.db.base import Base

ROLES = ("patient", "researcher", "clinician", "admin")
_ROLES_SQL = ", ".join(f"'{r}'" for r in ROLES)

CONSENT_SCOPES = ("app_use", "research_data")
AUDIT_EVENTS = (
    "login_ok",
    "login_failed",
    "register",
    "logout",
    "token_reuse",
    "account_deleted",
    "data_export",
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class AppUser(Base):
    __tablename__ = "app_user"
    __table_args__ = (CheckConstraint(f"role IN ({_ROLES_SQL})", name="role_known"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(16), default="patient")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# One account per e-mail address, whatever its letter case.
Index("uq_app_user_email_lower", func.lower(AppUser.email), unique=True)


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("core.app_user.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    user_agent: Mapped[str | None] = mapped_column(String(255))


class Consent(Base):
    __tablename__ = "consent"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("core.app_user.id", ondelete="CASCADE"), index=True
    )
    consent_version: Mapped[str] = mapped_column(String(32))
    scope: Mapped[str] = mapped_column(String(32))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    """What happened, not what was said: no passwords, no health data, no raw IP address."""

    __tablename__ = "audit_event"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    event: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip_hash: Mapped[str | None] = mapped_column(String(64))
