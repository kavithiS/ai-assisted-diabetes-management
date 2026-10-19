"""Storage behind one interface: Postgres (`SqlAssessmentStore`) or memory (tests).

The service layer only sees `AssessmentStore`. Saving is best-effort: if the database
is down, the assessment is still answered and the response says it was not saved.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import Engine, create_engine, delete, select, text
from sqlalchemy.orm import Session

from c3_risk_xai.db.models import (
    SCHEMA,
    AssessmentRow,
    AuditLogRow,
    DhsHistoryRow,
    RiskProfileRow,
)


@dataclass(frozen=True)
class StoredAssessment:
    """One history entry: no answers, only what the history screen needs."""

    id: str
    created_at: datetime
    status: str
    band: str | None
    model_version: str | None
    schema_version: str
    dhs: float | None


@dataclass(frozen=True)
class NewAssessment:
    device_id: str
    schema_version: str
    answers: dict[str, Any]
    status: str
    band: str | None
    model_version: str | None
    model_used: str | None
    feature_set: str | None
    explanation: dict[str, Any] | None
    dhs: float | None = None
    dhs_components: dict[str, Any] | None = None


class AssessmentStore(Protocol):
    def ping(self) -> bool: ...

    def save(self, record: NewAssessment) -> str: ...

    def history(self, device_id: str, limit: int = 50) -> list[StoredAssessment]: ...

    def delete_device(self, device_id: str) -> int: ...

    def last_dhs(self, device_id: str) -> float | None: ...


def sqlalchemy_url(database_url: str) -> str:
    """Use the psycopg 3 driver for a plain postgresql:// URL from the environment."""
    for prefix in ("postgresql://", "postgres://"):
        if database_url.startswith(prefix):
            return "postgresql+psycopg://" + database_url[len(prefix) :]
    return database_url


def make_engine(database_url: str) -> Engine:
    # Short connect timeout: a stopped database must not stall an assessment.
    return create_engine(
        sqlalchemy_url(database_url),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


class SqlAssessmentStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def ping(self) -> bool:
        """True when Postgres answers AND the c3 tables exist (alembic upgrade head ran)."""
        with self._engine.connect() as connection:
            found = connection.execute(
                text("SELECT to_regclass(:name)"), {"name": f"{SCHEMA}.assessments"}
            ).scalar()
        return found is not None

    def save(self, record: NewAssessment) -> str:
        with Session(self._engine) as session, session.begin():
            profile = RiskProfileRow(
                device_id=record.device_id,
                schema_version=record.schema_version,
                answers=record.answers,
            )
            session.add(profile)
            session.flush()
            row = AssessmentRow(
                device_id=record.device_id,
                profile_id=profile.id,
                schema_version=record.schema_version,
                model_version=record.model_version,
                model_used=record.model_used,
                feature_set=record.feature_set,
                status=record.status,
                band=record.band,
                dhs=record.dhs,
                explanation=record.explanation,
            )
            session.add(row)
            session.flush()
            if record.dhs is not None:
                session.add(
                    DhsHistoryRow(
                        device_id=record.device_id,
                        assessment_id=row.id,
                        score=record.dhs,
                        components=record.dhs_components or {},
                    )
                )
            session.add(
                AuditLogRow(device_id=record.device_id, action="assess", detail=record.status)
            )
            return str(row.id)

    def last_dhs(self, device_id: str) -> float | None:
        """Latest DHS of this device, for the adaptive (smoothed) score."""
        with Session(self._engine) as session:
            return session.scalar(
                select(DhsHistoryRow.score)
                .where(DhsHistoryRow.device_id == device_id)
                .order_by(DhsHistoryRow.created_at.desc())
                .limit(1)
            )

    def history(self, device_id: str, limit: int = 50) -> list[StoredAssessment]:
        with Session(self._engine) as session, session.begin():
            rows = session.scalars(
                select(AssessmentRow)
                .where(AssessmentRow.device_id == device_id)
                .order_by(AssessmentRow.created_at.desc())
                .limit(limit)
            ).all()
            session.add(
                AuditLogRow(device_id=device_id, action="history_read", detail=str(len(rows)))
            )
            return [
                StoredAssessment(
                    id=str(r.id),
                    created_at=r.created_at,
                    status=r.status,
                    band=r.band,
                    model_version=r.model_version,
                    schema_version=r.schema_version,
                    dhs=r.dhs,
                )
                for r in rows
            ]

    def delete_device(self, device_id: str) -> int:
        """FR16: remove the device's profiles (assessments and DHS rows cascade). The audit
        entry keeps only the pseudonym, the action and the count."""
        with Session(self._engine) as session, session.begin():
            count = len(
                session.scalars(
                    select(AssessmentRow.id).where(AssessmentRow.device_id == device_id)
                ).all()
            )
            session.execute(delete(RiskProfileRow).where(RiskProfileRow.device_id == device_id))
            session.add(
                AuditLogRow(device_id=device_id, action="delete_device_records", detail=str(count))
            )
            return count


@dataclass
class InMemoryAssessmentStore:
    """Same behaviour without a database: unit tests and local runs without Postgres."""

    rows: list[tuple[str, NewAssessment, datetime]] = field(default_factory=list)
    audit: list[tuple[str, str, str]] = field(default_factory=list)
    available: bool = True

    def ping(self) -> bool:
        self._check()  # behaves like a stopped database: raises, like the real driver
        return True

    def _check(self) -> None:
        if not self.available:
            raise ConnectionError("in-memory store switched off")

    def save(self, record: NewAssessment) -> str:
        self._check()
        record_id = str(uuid.uuid4())
        self.rows.append((record_id, record, datetime.now(UTC)))
        self.audit.append((record.device_id, "assess", record.status))
        return record_id

    def last_dhs(self, device_id: str) -> float | None:
        self._check()
        scores = [
            r[1].dhs for r in self.rows if r[1].device_id == device_id and r[1].dhs is not None
        ]
        return scores[-1] if scores else None

    def history(self, device_id: str, limit: int = 50) -> list[StoredAssessment]:
        self._check()
        mine = [r for r in reversed(self.rows) if r[1].device_id == device_id][:limit]
        self.audit.append((device_id, "history_read", str(len(mine))))
        return [
            StoredAssessment(
                id=record_id,
                created_at=created,
                status=record.status,
                band=record.band,
                model_version=record.model_version,
                schema_version=record.schema_version,
                dhs=record.dhs,
            )
            for record_id, record, created in mine
        ]

    def delete_device(self, device_id: str) -> int:
        self._check()
        before = len(self.rows)
        self.rows = [r for r in self.rows if r[1].device_id != device_id]
        count = before - len(self.rows)
        self.audit.append((device_id, "delete_device_records", str(count)))
        return count
