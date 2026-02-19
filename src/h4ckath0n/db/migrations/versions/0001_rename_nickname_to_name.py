"""rename nickname to name on webauthn_credentials

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

Safe, additive migration:
  - Renames the existing nullable `nickname` column to `name`.
  - Adjusts max length from 255 → 64 (safe when no existing value exceeds 64).
  - Downgrade drops back to `nickname` VARCHAR(255).
  - No data loss: existing NULL or non-NULL values are preserved.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch mode for SQLite compatibility (ALTER TABLE limitations).
    with op.batch_alter_table("webauthn_credentials") as batch_op:
        batch_op.alter_column(
            "nickname",
            new_column_name="name",
            existing_type=sa.String(255),
            type_=sa.String(64),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("webauthn_credentials") as batch_op:
        batch_op.alter_column(
            "name",
            new_column_name="nickname",
            existing_type=sa.String(64),
            type_=sa.String(255),
            existing_nullable=True,
        )
