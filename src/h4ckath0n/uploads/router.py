"""Uploads API router."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from h4ckath0n.auth.dependencies import require_user
from h4ckath0n.auth.models import User
from h4ckath0n.uploads.models import Upload
from h4ckath0n.uploads.schemas import UploadResponse
from h4ckath0n.uploads.storage import get_file_path, store_file

logger = logging.getLogger(__name__)

uploads_router = APIRouter(prefix="/uploads", tags=["uploads"])

# Content types eligible for extraction.
_TEXT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "text/html",
}


async def _db_dep(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.async_session_factory() as db:
        yield db


def _upload_to_response(u: Upload) -> UploadResponse:
    return UploadResponse(
        id=u.id,
        original_filename=u.original_filename,
        content_type=u.content_type,
        byte_size=u.byte_size,
        sha256=u.sha256,
        extraction_job_id=u.extraction_job_id,
        created_at=u.created_at,
    )


@uploads_router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    description="Upload a file (multipart/form-data).",
)
async def upload_file(
    file: UploadFile,
    request: Request,
    user: User = require_user(),
    db: AsyncSession = Depends(_db_dep),
) -> UploadResponse:
    settings = request.app.state.settings
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_bytes} bytes",
        )

    # 🛡️ Sentinel: Prevent OOM DoS by bounding the read
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_bytes} bytes",
        )

    storage_key, sha256 = await store_file(settings.storage_dir, data)
    content_type = file.content_type or "application/octet-stream"

    upload = Upload(
        owner_user_id=user.id,
        original_filename=file.filename or "upload",
        content_type=content_type,
        byte_size=len(data),
        sha256=sha256,
        storage_key=storage_key,
    )
    db.add(upload)
    await db.commit()
    await db.refresh(upload)

    # Queue extraction for text-like files.
    if content_type in _TEXT_TYPES:
        try:
            import h4ckath0n.jobs.handlers  # noqa: F401 – ensure handlers registered
            from h4ckath0n.jobs.queue import enqueue_job

            job = await enqueue_job(
                db,
                "uploads.extract_text",
                {
                    "storage_key": storage_key,
                    "storage_dir": settings.storage_dir,
                    "upload_id": upload.id,
                },
                user_id=user.id,
                redis_url=settings.redis_url,
                inline=settings.jobs_inline_in_dev,
            )
            upload.extraction_job_id = job.id
            await db.commit()
            await db.refresh(upload)
        except Exception:
            # Extraction failure must not fail the upload; log it.
            logger.exception(
                "Failed to enqueue text extraction for upload %s", upload.id
            )

    return _upload_to_response(upload)


@uploads_router.get(
    "",
    response_model=list[UploadResponse],
    summary="List uploads",
    description="List uploads for the current user.",
)
async def list_uploads(
    user: User = require_user(),
    db: AsyncSession = Depends(_db_dep),
) -> list[UploadResponse]:
    result = await db.execute(
        select(Upload)
        .filter(Upload.owner_user_id == user.id)
        .order_by(Upload.created_at.desc())
        .limit(50)
    )
    return [_upload_to_response(u) for u in result.scalars()]


@uploads_router.get(
    "/{upload_id}",
    response_model=UploadResponse,
    summary="Get upload metadata",
)
async def get_upload(
    upload_id: str,
    user: User = require_user(),
    db: AsyncSession = Depends(_db_dep),
) -> UploadResponse:
    # Use db.get() for primary key lookup.
    upload = await db.get(Upload, upload_id)
    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        )
    if upload.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    return _upload_to_response(upload)


@uploads_router.get(
    "/{upload_id}/download",
    summary="Download a file",
    description="Stream the file back to the owner.",
)
async def download_upload(
    upload_id: str,
    request: Request,
    user: User = require_user(),
    db: AsyncSession = Depends(_db_dep),
) -> FileResponse:
    # Use db.get() for primary key lookup.
    upload = await db.get(Upload, upload_id)
    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found"
        )
    if upload.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    settings = request.app.state.settings
    try:
        file_path = get_file_path(settings.storage_dir, upload.storage_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage key"
        ) from exc

    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk"
        )

    return FileResponse(
        path=file_path,
        media_type=upload.content_type,
        filename=upload.original_filename,
    )
