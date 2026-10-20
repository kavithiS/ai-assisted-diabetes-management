"""create meal history tables

Revision ID: c3e5a1b7d2f4
Revises: 78ab001a889d
Create Date: 2026-10-16 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3e5a1b7d2f4"
down_revision: str | Sequence[str] | None = "78ab001a889d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "meal",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("eaten_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meal_type", sa.String(length=16), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "meal_type IS NULL OR meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')",
            name=op.f("ck_meal_meal_type_known"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meal")),
    )
    op.create_index(op.f("ix_meal_eaten_at"), "meal", ["eaten_at"], unique=False)
    op.create_table(
        "meal_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("meal_id", sa.Integer(), nullable=False),
        sa.Column("food_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("grams", sa.Float(), nullable=False),
        sa.Column("energy_kcal", sa.Float(), nullable=True),
        sa.Column("carbohydrate_g", sa.Float(), nullable=True),
        sa.Column("sugars_g", sa.Float(), nullable=True),
        sa.Column("dietary_fiber_g", sa.Float(), nullable=True),
        sa.Column("protein_g", sa.Float(), nullable=True),
        sa.Column("fat_g", sa.Float(), nullable=True),
        sa.Column("sodium_mg", sa.Float(), nullable=True),
        sa.CheckConstraint("grams > 0", name=op.f("ck_meal_item_grams_positive")),
        sa.ForeignKeyConstraint(
            ["food_id"], ["food.id"], name=op.f("fk_meal_item_food_id_food"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["meal_id"], ["meal.id"], name=op.f("fk_meal_item_meal_id_meal"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meal_item")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("meal_item")
    op.drop_index(op.f("ix_meal_eaten_at"), table_name="meal")
    op.drop_table("meal")
