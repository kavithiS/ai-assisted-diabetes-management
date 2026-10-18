"""add patient_id to meal

Existing demo meals are assigned to the fixed demo patient (decision D4, proposed default);
the gateway uses the same id as DEMO_PATIENT_ID while the app has no login.

Revision ID: d4a6c2f8b913
Revises: c3e5a1b7d2f4
Create Date: 2026-10-18 12:00:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a6c2f8b913"
down_revision: str | Sequence[str] | None = "c3e5a1b7d2f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_PATIENT_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("meal") as batch:
        batch.add_column(sa.Column("patient_id", sa.Uuid(), nullable=True))

    op.get_bind().execute(
        sa.text("UPDATE meal SET patient_id = :pid").bindparams(
            sa.bindparam("pid", value=DEMO_PATIENT_ID, type_=sa.Uuid())
        )
    )

    with op.batch_alter_table("meal") as batch:
        batch.alter_column("patient_id", existing_type=sa.Uuid(), nullable=False)

    op.create_index("ix_meal_patient_eaten", "meal", ["patient_id", sa.text("eaten_at DESC")])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_meal_patient_eaten", table_name="meal")
    with op.batch_alter_table("meal") as batch:
        batch.drop_column("patient_id")
