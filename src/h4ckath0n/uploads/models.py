"""Upload SQLAlchemy models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from h4ckath0n.auth.passkeys.ids import random_base32
from h4ckath0n.db.base import Base, utcnow


def new_upload_id() -> str:
    """Generate an upload ID (32 chars, starts with 'f')."""
    s = random_base32()
    return "f" + s[1:]


class Upload(Base):
    __tablename__ = "h4ckath0n_uploads"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_upload_id)
    owner_user_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(255), nullable=False, default="application/octet-stream"
    )
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    extraction_job_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
