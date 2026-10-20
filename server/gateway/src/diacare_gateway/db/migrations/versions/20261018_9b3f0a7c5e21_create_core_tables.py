"""create core tables

Users, refresh tokens, consent and audit events (ADR 0005, 0006). SQLite has no schemas, so
the tables are created without one there (unit tests only).

Revision ID: 9b3f0a7c5e21
Revises: None
Create Date: 2026-10-18 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b3f0a7c5e21"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLES = "'patient', 'researcher', 'clinician', 'admin'"


def _schema() -> tuple[str | None, str]:
    """(schema for op calls, prefix for foreign key targets)."""
    if op.get_bind().dialect.name == "sqlite":
        return None, ""
    return "core", "core."


def upgrade() -> None:
    """Upgrade schema."""
    schema, prefix = _schema()

    op.create_table(
        "app_user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"role IN ({ROLES})", name="ck_app_user_role_known"),
        sa.PrimaryKeyConstraint("id", name="pk_app_user"),
        schema=schema,
    )
    op.create_index(
        "uq_app_user_email_lower", "app_user", [sa.text("lower(email)")], unique=True, schema=schema
    )

    op.create_table(
        "refresh_token",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", sa.Uuid(), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{prefix}app_user.id"],
            name="fk_refresh_token_user_id_app_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_token"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_token_token_hash"),
        schema=schema,
    )
    op.create_index("ix_refresh_token_user_id", "refresh_token", ["user_id"], schema=schema)

    op.create_table(
        "consent",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("consent_version", sa.String(length=32), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{prefix}app_user.id"],
            name="fk_consent_user_id_app_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_consent"),
        schema=schema,
    )
    op.create_index("ix_consent_user_id", "consent", ["user_id"], schema=schema)

    op.create_table(
        "audit_event",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("event", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_audit_event"),
        schema=schema,
    )


def downgrade() -> None:
    """Downgrade schema."""
    schema, _ = _schema()
    op.drop_table("audit_event", schema=schema)
    op.drop_index("ix_consent_user_id", table_name="consent", schema=schema)
    op.drop_table("consent", schema=schema)
    op.drop_index("ix_refresh_token_user_id", table_name="refresh_token", schema=schema)
    op.drop_table("refresh_token", schema=schema)
    op.drop_index("uq_app_user_email_lower", table_name="app_user", schema=schema)
    op.drop_table("app_user", schema=schema)
