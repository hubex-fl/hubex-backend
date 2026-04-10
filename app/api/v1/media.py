"""Media Library API — upload, list, serve, delete media assets.

Storage layout:
  <MEDIA_ROOT>/<yyyy>/<mm>/<uuid><ext>          — original file
  <MEDIA_ROOT>/<yyyy>/<mm>/thumbs/<uuid>.jpg    — thumbnail (images only)
"""
from __future__ import annotations

import mimetypes
import os
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy import delete as sql_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.media_asset import MediaAsset
from app.db.models.user import User
from app.schemas.media import MediaAssetListOut, MediaAssetOut, MediaAssetUpdate

router = APIRouter(prefix="/media", tags=["media"])

# ── Config ───────────────────────────────────────────────────────────────
MEDIA_ROOT = Path(os.environ.get("HUBEX_MEDIA_ROOT", "/app/data/media"))
try:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
except Exception:
    # Fallback to a path under the working directory
    MEDIA_ROOT = Path.cwd() / "data" / "media"
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_PREFIXES = ("image/", "video/", "audio/")
ALLOWED_MIME_EXACT = {
    "application/pdf",
    # Office documents
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # pptx
    # Archives
    "application/zip",
    "application/x-zip-compressed",
    "application/x-tar",
    "application/gzip",
    "application/x-7z-compressed",
}
THUMBNAIL_SIZE = (256, 256)


def _asset_kind(mime: str) -> str:
    """Classify a mime type as images|videos|audio|documents|archives|other."""
    if not mime:
        return "other"
    if mime.startswith("image/"):
        return "images"
    if mime.startswith("video/"):
        return "videos"
    if mime.startswith("audio/"):
        return "audio"
    if mime == "application/pdf" or mime.startswith("application/vnd.openxmlformats-") or mime in (
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
    ):
        return "documents"
    if mime in (
        "application/zip",
        "application/x-zip-compressed",
        "application/x-tar",
        "application/gzip",
        "application/x-7z-compressed",
    ):
        return "archives"
    return "other"


# ── Helpers ──────────────────────────────────────────────────────────────

def _is_allowed_mime(mime: str) -> bool:
    if not mime:
        return False
    if any(mime.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        return True
    if mime in ALLOWED_MIME_EXACT:
        return True
    return False


def _mime_from_filename(filename: str) -> str:
    guess, _ = mimetypes.guess_type(filename)
    return guess or "application/octet-stream"


def _ext_from_mime(mime: str, fallback: str) -> str:
    ext = mimetypes.guess_extension(mime or "")
    if ext:
        return ext
    return fallback or ".bin"


def _asset_out(a: MediaAsset) -> MediaAssetOut:
    thumb_url: Optional[str] = None
    if a.thumbnail_path:
        thumb_url = f"/api/v1/media/{a.id}/thumbnail"
    return MediaAssetOut(
        id=a.id,
        filename=a.filename,
        public_url=a.public_url,
        mime_type=a.mime_type,
        size_bytes=a.size_bytes,
        width=a.width,
        height=a.height,
        alt_text=a.alt_text,
        thumbnail_url=thumb_url,
        kind=_asset_kind(a.mime_type or ""),
        created_at=a.created_at,
    )


def _generate_thumbnail(src_path: Path, dst_dir: Path, uid: str) -> Optional[Path]:
    """Generate a 256x256 max thumbnail for images. Returns path or None."""
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = dst_dir / f"{uid}.jpg"
        with Image.open(src_path) as im:
            im = im.convert("RGB") if im.mode not in ("RGB", "L") else im
            im.thumbnail(THUMBNAIL_SIZE)
            im.save(thumb_path, "JPEG", quality=82, optimize=True)
        return thumb_path
    except Exception:
        return None


def _image_dimensions(src_path: Path) -> tuple[Optional[int], Optional[int]]:
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None, None
    try:
        with Image.open(src_path) as im:
            return im.width, im.height
    except Exception:
        return None, None


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/upload", response_model=MediaAssetOut, status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a new media asset. Max 20MB. Images, videos, PDFs."""
    # Determine mime type
    mime = file.content_type or _mime_from_filename(file.filename or "")
    if not _is_allowed_mime(mime):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported media type: {mime}",
        )

    # Read and enforce size limit (stream)
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large (max 20MB)")
        chunks.append(chunk)
    data = b"".join(chunks)

    # Build storage path
    now = datetime.now(timezone.utc)
    subdir = MEDIA_ROOT / f"{now.year:04d}" / f"{now.month:02d}"
    subdir.mkdir(parents=True, exist_ok=True)

    uid = _uuid.uuid4().hex
    # Preserve original extension when possible
    orig_name = file.filename or "upload"
    _, orig_ext = os.path.splitext(orig_name)
    ext = orig_ext.lower() if orig_ext else _ext_from_mime(mime, ".bin")
    stored_name = f"{uid}{ext}"
    stored_path = subdir / stored_name
    try:
        stored_path.write_bytes(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Image metadata + thumbnail
    width = height = None
    thumbnail_path: Optional[str] = None
    if mime.startswith("image/"):
        width, height = _image_dimensions(stored_path)
        thumb = _generate_thumbnail(stored_path, subdir / "thumbs", uid)
        if thumb is not None:
            thumbnail_path = str(thumb)

    # Create record
    asset = MediaAsset(
        org_id=getattr(current_user, "org_id", None),
        owner_id=current_user.id,
        filename=orig_name,
        stored_path=str(stored_path),
        public_url="",  # set after insert so we know the id
        mime_type=mime,
        size_bytes=size,
        width=width,
        height=height,
        alt_text=alt_text,
        thumbnail_path=thumbnail_path,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    asset.public_url = f"/api/v1/media/{asset.id}/file"
    await db.commit()
    await db.refresh(asset)
    return _asset_out(asset)


@router.get("", response_model=MediaAssetListOut)
async def list_media(
    kind: Optional[str] = Query(
        default=None, description="Filter: images|videos|documents"
    ),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=40, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(MediaAsset).where(MediaAsset.owner_id == current_user.id)
    count_stmt = select(func.count()).select_from(MediaAsset).where(
        MediaAsset.owner_id == current_user.id
    )
    if kind == "images":
        stmt = stmt.where(MediaAsset.mime_type.like("image/%"))
        count_stmt = count_stmt.where(MediaAsset.mime_type.like("image/%"))
    elif kind == "videos":
        stmt = stmt.where(MediaAsset.mime_type.like("video/%"))
        count_stmt = count_stmt.where(MediaAsset.mime_type.like("video/%"))
    elif kind == "audio":
        stmt = stmt.where(MediaAsset.mime_type.like("audio/%"))
        count_stmt = count_stmt.where(MediaAsset.mime_type.like("audio/%"))
    elif kind == "documents":
        doc_mimes = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ]
        stmt = stmt.where(MediaAsset.mime_type.in_(doc_mimes))
        count_stmt = count_stmt.where(MediaAsset.mime_type.in_(doc_mimes))
    elif kind == "archives":
        arc_mimes = [
            "application/zip",
            "application/x-zip-compressed",
            "application/x-tar",
            "application/gzip",
            "application/x-7z-compressed",
        ]
        stmt = stmt.where(MediaAsset.mime_type.in_(arc_mimes))
        count_stmt = count_stmt.where(MediaAsset.mime_type.in_(arc_mimes))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(MediaAsset.filename.ilike(pattern))
        count_stmt = count_stmt.where(MediaAsset.filename.ilike(pattern))
    stmt = stmt.order_by(MediaAsset.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    total = (await db.execute(count_stmt)).scalar() or 0
    res = await db.execute(stmt)
    assets = list(res.scalars().all())
    return MediaAssetListOut(
        items=[_asset_out(a) for a in assets],
        total=int(total),
        page=page,
        page_size=page_size,
    )


@router.get("/{asset_id}", response_model=MediaAssetOut)
async def get_media(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(MediaAsset).where(
            MediaAsset.id == asset_id,
            MediaAsset.owner_id == current_user.id,
        )
    )
    a = res.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _asset_out(a)


@router.get("/{asset_id}/file")
async def get_media_file(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Public file serving — no auth required (whitelisted).

    Safe: we only serve files under MEDIA_ROOT from DB-tracked rows.
    """
    res = await db.execute(select(MediaAsset).where(MediaAsset.id == asset_id))
    a = res.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Asset not found")
    p = Path(a.stored_path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="File missing from storage")
    return FileResponse(
        path=str(p),
        media_type=a.mime_type,
        filename=a.filename,
    )


@router.get("/{asset_id}/thumbnail")
async def get_media_thumbnail(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Public thumbnail — no auth required."""
    res = await db.execute(select(MediaAsset).where(MediaAsset.id == asset_id))
    a = res.scalar_one_or_none()
    if not a or not a.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not available")
    p = Path(a.thumbnail_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Thumbnail missing")
    return FileResponse(path=str(p), media_type="image/jpeg")


@router.put("/{asset_id}", response_model=MediaAssetOut)
async def update_media(
    asset_id: int,
    data: MediaAssetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(MediaAsset).where(
            MediaAsset.id == asset_id,
            MediaAsset.owner_id == current_user.id,
        )
    )
    a = res.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Asset not found")
    if data.alt_text is not None:
        a.alt_text = data.alt_text
    if data.filename is not None:
        a.filename = data.filename
    await db.commit()
    await db.refresh(a)
    return _asset_out(a)


@router.delete("/{asset_id}", status_code=204)
async def delete_media(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(MediaAsset).where(
            MediaAsset.id == asset_id,
            MediaAsset.owner_id == current_user.id,
        )
    )
    a = res.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Asset not found")
    # Best-effort file cleanup
    for path in (a.stored_path, a.thumbnail_path):
        if not path:
            continue
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass
    await db.execute(sql_delete(MediaAsset).where(MediaAsset.id == a.id))
    await db.commit()
