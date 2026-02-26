"""Initial h4ckath0n schema.

Revision ID: 0001
Revises: None
Create Date: 2025-01-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "h4ckath0n_users",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("scopes", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("password_hash", sa.Text, nullable=True),
    )
    op.create_index("ix_h4ckath0n_users_email", "h4ckath0n_users", ["email"], unique=True)

    op.create_table(
        "h4ckath0n_webauthn_credentials",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), nullable=False),
        sa.Column("credential_id", sa.Text, nullable=False),
        sa.Column("public_key", sa.LargeBinary, nullable=False),
        sa.Column("sign_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("aaguid", sa.String(36), nullable=True),
        sa.Column("transports", sa.Text, nullable=True),
        sa.Column("nickname", sa.String(255), nullable=True),  # Original name
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("credential_id", name="uq_h4ckath0n_webauthn_credential_id"),
    )
    op.create_index("ix_h4ckath0n_webauthn_credentials_user_id", "h4ckath0n_webauthn_credentials", ["user_id"])

    op.create_table(
        "h4ckath0n_webauthn_challenges",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("challenge", sa.Text, nullable=False),
        sa.Column("user_id", sa.String(32), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rp_id", sa.String(255), nullable=False),
        sa.Column("origin", sa.String(512), nullable=False),
    )
    op.create_index("ix_h4ckath0n_webauthn_challenges_expires_at", "h4ckath0n_webauthn_challenges", ["expires_at"])

    op.create_table(
        "h4ckath0n_password_reset_tokens",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_h4ckath0n_password_reset_token_hash"),
    )
    op.create_index("ix_h4ckath0n_password_reset_tokens_user_id", "h4ckath0n_password_reset_tokens", ["user_id"])

    op.create_table(
        "h4ckath0n_devices",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), nullable=False),
        sa.Column("public_key_jwk", sa.Text, nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_h4ckath0n_devices_user_id", "h4ckath0n_devices", ["user_id"])
    op.create_index("ix_h4ckath0n_devices_fingerprint", "h4ckath0n_devices", ["fingerprint"], unique=True)


def downgrade() -> None:
    op.drop_table("h4ckath0n_devices")
    op.drop_table("h4ckath0n_password_reset_tokens")
    op.drop_table("h4ckath0n_webauthn_challenges")
    op.drop_table("h4ckath0n_webauthn_credentials")
    op.drop_table("h4ckath0n_users")
