"""SQLAlchemy 2 tables for C3. Everything lives in the Postgres schema `c3` (ADR: one
schema per component); C3 never reads or writes c1, c2 or c4.

Privacy (NFR4, NFR12): rows are keyed by a random device pseudonym made by the app, never
by a name or contact. The audit log records actions and counts, never health answers.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, MetaData, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA = "c3"

# JSONB on Postgres, plain JSON elsewhere (the in-memory tests never create tables).
Json = JSON().with_variant(JSONB(), "postgresql")


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)


class RiskProfileRow(Base):
    """One questionnaire submission, exactly as sent (versioned answers)."""

    __tablename__ = "risk_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    schema_version: Mapped[str] = mapped_column(String(16))
    answers: Mapped[dict[str, Any]] = mapped_column(Json)
    # Demo data only until ethics approval; a real consent screen sets this in PP2.
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AssessmentRow(Base):
    """One C3 answer for one profile (FR13 history, FR15 versions, NFR12 audit trail)."""

    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{SCHEMA}.risk_profiles.id", ondelete="CASCADE")
    )
    schema_version: Mapped[str] = mapped_column(String(16))
    model_version: Mapped[str | None] = mapped_column(String(32))
    model_used: Mapped[str | None] = mapped_column(String(64))
    feature_set: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    band: Mapped[str | None] = mapped_column(String(16))
    dhs: Mapped[float | None] = mapped_column(Float)
    # Factors with direction, rank and evidence level (real_data / synthetic_assumption).
    explanation: Mapped[dict[str, Any] | None] = mapped_column(Json)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class DhsHistoryRow(Base):
    """Diabetic Health Score over time (adaptive DHS, TAF task 4)."""

    __tablename__ = "dhs_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.assessments.id", ondelete="CASCADE")
    )
    score: Mapped[float] = mapped_column(Float)
    components: Mapped[dict[str, Any]] = mapped_column(Json)
    provisional: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLogRow(Base):
    """Who did what and when. No health answers or results are stored here."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(48))
    detail: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ExternalInputRow(Base):
    """Snapshots of C1 nutrition / C2 forecast payloads. MOCK until a contract exists."""

    __tablename__ = "external_inputs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(8))  # "C1" or "C2"
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)
    source_version: Mapped[str | None] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(Json)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
