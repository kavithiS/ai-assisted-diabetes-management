"""C3 initial tables: risk_profiles, assessments, dhs_history, audit_log, external_inputs.

Revision ID: 0001_c3_initial
Revises:
Create Date: 2026-10-19
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_c3_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "c3"


def _id() -> sa.Column[Any]:
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _device() -> sa.Column[Any]:
    return sa.Column("device_id", sa.String(64), nullable=False, index=True)


def _created(name: str = "created_at") -> sa.Column[Any]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.create_table(
        "risk_profiles",
        _id(),
        _device(),
        sa.Column("schema_version", sa.String(16), nullable=False),
        sa.Column("answers", postgresql.JSONB(), nullable=False),
        sa.Column("consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        _created(),
        schema=SCHEMA,
    )
    op.create_table(
        "assessments",
        _id(),
        _device(),
        sa.Column(
            "profile_id",
            sa.Uuid(),
            sa.ForeignKey(f"{SCHEMA}.risk_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("schema_version", sa.String(16), nullable=False),
        sa.Column("model_version", sa.String(32)),
        sa.Column("model_used", sa.String(64)),
        sa.Column("feature_set", sa.String(32)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("band", sa.String(16)),
        sa.Column("dhs", sa.Float()),
        sa.Column("explanation", postgresql.JSONB()),
        _created(),
        schema=SCHEMA,
    )
    op.create_index("ix_c3_assessments_created_at", "assessments", ["created_at"], schema=SCHEMA)
    op.create_table(
        "dhs_history",
        _id(),
        _device(),
        sa.Column(
            "assessment_id",
            sa.Uuid(),
            sa.ForeignKey(f"{SCHEMA}.assessments.id", ondelete="CASCADE"),
        ),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("components", postgresql.JSONB(), nullable=False),
        sa.Column("provisional", sa.Boolean(), nullable=False, server_default=sa.true()),
        _created(),
        schema=SCHEMA,
    )
    op.create_table(
        "audit_log",
        _id(),
        _device(),
        sa.Column("action", sa.String(48), nullable=False),
        sa.Column("detail", sa.String(200)),
        _created(),
        schema=SCHEMA,
    )
    op.create_table(
        "external_inputs",
        _id(),
        _device(),
        sa.Column("source", sa.String(8), nullable=False),
        sa.Column("is_mock", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("source_version", sa.String(32)),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        _created("received_at"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    for table in ("external_inputs", "audit_log", "dhs_history", "assessments", "risk_profiles"):
        op.drop_table(table, schema=SCHEMA)
