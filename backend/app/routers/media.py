# -*- coding: utf-8 -*-
"""Медиатека: загрузка изображений для карточек.

Загрузка идёт «сырым» телом запроса (POST /media?filename=..&kind=..), а не multipart:
файл пишется на диск кусками и не копится в памяти, а отдельная зависимость
python-multipart не нужна. Тип изображения определяется по байтам, расширение
файла — по белому списку; имя на диске генерируется сервером.
Загружать могут только сотрудники: суперадмин и администраторы факультетов.
"""
import hashlib
import os
import uuid
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .. import auth, models, schemas, uploads
from ..database import SessionLocal, get_db

router = APIRouter(prefix="/media", tags=["media"])

# Каталог лежит в томе ./backend/data, поэтому файлы переживают пересборку контейнера.
# «or»: docker-compose передаёт незаданные переменные как пустые строки.
MEDIA_DIR = Path(os.getenv("MEDIA_DIR") or "/app/data/media")
MAX_IMAGE_BYTES = int(float(os.getenv("MAX_IMAGE_MB") or 5) * 1024 * 1024)
MAX_FILE_BYTES = int(float(os.getenv("MAX_FILE_MB") or 500) * 1024 * 1024)

# disk — файлы на диске (по умолчанию, для своего сервера и локального запуска).
# db — изображения в базе данных: нужно там, где диска нет или он стирается при перезапуске
# (бесплатный тариф Render). Изображения небольшие (до MAX_IMAGE_MB), поэтому базе это по силам.
USE_DB = (os.getenv("MEDIA_STORAGE") or "disk").strip().lower() == "db"

IMAGE_HEADERS = {
    "Cache-Control": "public, max-age=31536000, immutable",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; sandbox",
}


def media_url(media_id) -> Optional[str]:
    """Путь к изображению для <img>; None, если файла нет."""
    return f"/media/{media_id}/file" if isinstance(media_id, int) else None


def media_out(item: models.MediaFile) -> schemas.MediaOut:
    return schemas.MediaOut(
        id=item.id,
        kind=item.kind,
        filename=item.filename,
        mime_type=item.mime_type,
        size=item.size or 0,
        url=media_url(item.id) if item.kind == "image" else None,
        owner_id=item.owner_id,
        created_at=item.created_at,
    )


def _save_record(**values) -> schemas.MediaOut:
    # Отдельная сессия: функция выполняется в потоке пула, а не в потоке запроса
    with SessionLocal() as db:
        item = models.MediaFile(**values)
        db.add(item)
        db.commit()
        db.refresh(item)
        return media_out(item)


def _is_referenced(db: Session, media_id: int) -> bool:
    """Используется ли изображение в какой-либо карточке (обложка или галерея)."""
    if db.query(models.Card.id).filter(models.Card.cover_media_id == media_id).first():
        return True
    for (gallery,) in db.query(models.Card.gallery):
        if isinstance(gallery, list) and media_id in gallery:
            return True
    return False


@router.post("", response_model=schemas.MediaOut, status_code=201)
async def upload_media(
    request: Request,
    filename: str = Query(..., min_length=1, max_length=255),
    kind: Literal["image", "file"] = "image",
    current_user: models.User = Depends(auth.require_staff),
):
    owner_id = current_user.id
    limit = MAX_IMAGE_BYTES if kind == "image" else MAX_FILE_BYTES
    too_big = HTTPException(
        status_code=413, detail=f"Файл больше допустимого размера ({limit // (1024 * 1024)} МБ)"
    )
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise too_big

    if USE_DB:
        return await _upload_to_db(request, filename, kind, owner_id, limit, too_big)

    ext = None
    if kind == "file":
        ext = uploads.allowed_file_ext(filename)
        if ext is None:
            raise HTTPException(
                status_code=415,
                detail="Недопустимый тип файла. Разрешены: " + ", ".join(uploads.ALLOWED_FILE_EXTS),
            )

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    tmp_path = MEDIA_DIR / f"{token}.part"
    final_path = None
    digest = hashlib.sha256()
    size = 0
    head = b""

    try:
        with open(tmp_path, "wb") as out:
            async for chunk in request.stream():
                if not chunk:
                    continue
                if len(head) < 16:
                    head += chunk[: 16 - len(head)]
                size += len(chunk)
                if size > limit:
                    raise too_big
                digest.update(chunk)
                await run_in_threadpool(out.write, chunk)

        if size == 0:
            raise HTTPException(status_code=400, detail="Пустой файл")

        if kind == "image":
            mime = uploads.sniff_image(head)
            if mime is None:
                raise HTTPException(status_code=415, detail="Допустимы изображения PNG, JPEG, GIF и WebP")
            ext = uploads.IMAGE_EXT[mime]
        else:
            mime = "application/octet-stream"

        stored_name = f"{token}{ext}"
        final_path = MEDIA_DIR / stored_name
        os.replace(tmp_path, final_path)

        return await run_in_threadpool(
            _save_record,
            kind=kind,
            filename=uploads.safe_display_name(filename),
            stored_name=stored_name,
            mime_type=mime,
            size=size,
            sha256=digest.hexdigest(),
            owner_id=owner_id,
        )
    except BaseException:
        # Любой сбой, включая обрыв соединения: не оставляем недозагруженные файлы
        tmp_path.unlink(missing_ok=True)
        if final_path is not None:
            final_path.unlink(missing_ok=True)
        raise


async def _upload_to_db(request: Request, filename: str, kind: str, owner_id, limit: int, too_big: HTTPException):
    """Режим MEDIA_STORAGE=db: изображение читается в память (оно небольшое) и кладётся в базу."""
    if kind != "image":
        raise HTTPException(status_code=415, detail="В этом режиме хранения загружаются только изображения")

    buffer = bytearray()
    async for chunk in request.stream():
        if not chunk:
            continue
        buffer.extend(chunk)
        if len(buffer) > limit:
            raise too_big
    if not buffer:
        raise HTTPException(status_code=400, detail="Пустой файл")

    mime = uploads.sniff_image(bytes(buffer[:16]))
    if mime is None:
        raise HTTPException(status_code=415, detail="Допустимы изображения PNG, JPEG, GIF и WebP")

    data = bytes(buffer)
    return await run_in_threadpool(
        _save_record,
        kind="image",
        filename=uploads.safe_display_name(filename),
        stored_name=f"{uuid.uuid4().hex}{uploads.IMAGE_EXT[mime]}",
        mime_type=mime,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        owner_id=owner_id,
        data=data,
    )


@router.get("", response_model=List[schemas.MediaOut])
def list_media(
    kind: Optional[Literal["image", "file"]] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_staff),
):
    """Библиотека: суперадмин видит все файлы, администраторы — только свои."""
    query = db.query(models.MediaFile)
    if current_user.role != "superuser":
        query = query.filter(models.MediaFile.owner_id == current_user.id)
    if kind:
        query = query.filter(models.MediaFile.kind == kind)
    rows = query.order_by(models.MediaFile.id.desc()).offset(skip).limit(limit).all()
    return [media_out(item) for item in rows]


@router.get("/{media_id}/file")
def get_media_file(media_id: int, db: Session = Depends(get_db)):
    """Публично отдаётся только изображение."""
    item = (
        db.query(models.MediaFile)
        .filter(models.MediaFile.id == media_id, models.MediaFile.kind == "image")
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="File not found")
    if item.data is not None:  # изображение лежит в базе
        return Response(content=bytes(item.data), media_type=item.mime_type, headers=IMAGE_HEADERS)
    path = MEDIA_DIR / item.stored_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type=item.mime_type, headers=IMAGE_HEADERS)


@router.delete("/{media_id}")
def delete_media(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_staff),
):
    item = db.query(models.MediaFile).filter(models.MediaFile.id == media_id).first()
    if item is None or not (current_user.role == "superuser" or item.owner_id == current_user.id):
        raise HTTPException(status_code=404, detail="File not found")
    if _is_referenced(db, media_id):
        raise HTTPException(status_code=409, detail="Файл используется в карточке — сначала уберите его оттуда")

    path = MEDIA_DIR / item.stored_name
    db.delete(item)
    db.commit()
    path.unlink(missing_ok=True)
    return {"message": "Media deleted"}
