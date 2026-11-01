# -*- coding: utf-8 -*-
"""Карточки разработок вуза.

  * читать опубликованное может любой;
  * черновики видят суперадмин и администратор того же факультета;
  * создавать и менять карточки могут сотрудники: суперадмин (любой факультет) и
    администратор факультета (только свой). Это проверяется здесь, на сервере.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .. import auth, models, schemas
from ..database import get_db
from ..permissions import FacultyAccessError, can_manage_faculty, can_view_card, resolve_card_faculty
from ..sanitize import safe_url, sanitize_html
from ..search import SearchDoc, html_to_text, rank
from ..taxonomy import normalize_tag, normalize_tags
from .media import media_url

router = APIRouter(prefix="/cards", tags=["cards"])


# ---------------------------------------------------------------- представления
def _brief_data(card: models.Card) -> dict:
    return {
        "id": card.id,
        "title": card.title,
        "summary": card.summary,
        "faculty_id": card.faculty_id,
        "faculty_name": card.faculty.name,
        "faculty_short_name": card.faculty.short_name,
        "status": card.status,
        "readiness": card.readiness,
        "cover_url": media_url(card.cover_media_id),
        "tags": sorted(tag.name for tag in card.tags),
        "published_at": card.published_at,
        "updated_at": card.updated_at,
    }


def brief(card: models.Card) -> schemas.CardBrief:
    return schemas.CardBrief(**_brief_data(card))


def _can_manage(card: models.Card, user) -> bool:
    return user is not None and can_manage_faculty(user.role, user.faculty_id, card.faculty_id)


def detail(card: models.Card, user) -> schemas.CardOut:
    gallery = list(card.gallery or [])
    data = _brief_data(card)
    data.update(
        description=card.description,
        gallery_urls=[media_url(i) for i in gallery],
        cover_media_id=card.cover_media_id,
        gallery_media_ids=gallery,
        contact_name=card.contact_name,
        contact_email=card.contact_email,
        contact_phone=card.contact_phone,
        website=card.website,
        created_at=card.created_at,
        can_manage=_can_manage(card, user),
    )
    return schemas.CardOut(**data)


def _load(db: Session, card_id: int) -> Optional[models.Card]:
    return (
        db.query(models.Card)
        .options(joinedload(models.Card.faculty))
        .filter(models.Card.id == card_id)
        .first()
    )


def _get_manageable(db: Session, card_id: int, user) -> models.Card:
    card = _load(db, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    if not _can_manage(card, user):
        # Чужой черновик не раскрываем: для постороннего его «нет»
        if can_view_card(card.status, user.role, user.faculty_id, card.faculty_id):
            raise HTTPException(status_code=403, detail="Карточка принадлежит другому факультету")
        raise HTTPException(status_code=404, detail="Card not found")
    return card


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _search_doc(card: models.Card) -> SearchDoc:
    return SearchDoc(
        id=card.id,
        title=card.title,
        summary=card.summary,
        text=html_to_text(card.description),
        tags=[t.name for t in card.tags],
        faculty=card.faculty.name,
    )


# ---------------------------------------------------------------- проверка данных
def _invalid(message: str) -> HTTPException:
    return HTTPException(status_code=422, detail=message)


def _prepare(db: Session, user, payload: schemas.CardWrite, current_faculty_id, existing_media: set):
    """Проверяет данные карточки и приводит их к виду для сохранения.
    Возвращает (поля модели, список имён тегов)."""
    try:
        faculty_id = resolve_card_faculty(user.role, user.faculty_id, payload.faculty_id)
    except FacultyAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    if faculty_id is None:
        faculty_id = current_faculty_id  # суперадмин при правке без выбора факультета оставляет прежний
    if faculty_id is None:
        raise _invalid("Выберите факультет")
    if not db.query(models.Faculty.id).filter(models.Faculty.id == faculty_id).first():
        raise _invalid("Факультет не найден")

    # Изображения должны существовать и принадлежать автору (или уже стоять в этой карточке)
    wanted = [("Обложка", payload.cover_media_id)] + [("Галерея", i) for i in payload.gallery_media_ids]
    ids = [i for _, i in wanted if i]
    found = {}
    if ids:
        found = {m.id: m for m in db.query(models.MediaFile).filter(models.MediaFile.id.in_(ids))}
    for label, media_id in wanted:
        if not media_id:
            continue
        item = found.get(media_id)
        if item is None or item.kind != "image":
            raise _invalid(f"{label}: изображение #{media_id} не найдено в медиатеке")
        if user.role != "superuser" and item.owner_id != user.id and media_id not in existing_media:
            raise _invalid(f"{label}: изображение #{media_id} загружено другим пользователем")

    try:
        tag_names = normalize_tags(payload.tags)
    except ValueError as exc:
        raise _invalid(f"Теги: {exc}")

    website = (payload.website or "").strip() or None
    if website:
        checked = safe_url(website, allow_mailto=False)
        if not checked or not checked.startswith(("http://", "https://")):
            raise _invalid("Сайт: допустимы только адреса http:// и https://")
        website = checked

    description = sanitize_html(payload.description or "").strip() or None

    fields = {
        "faculty_id": faculty_id,
        "title": payload.title.strip(),
        "summary": payload.summary.strip(),
        "description": description,
        "status": payload.status,
        "readiness": payload.readiness,
        "cover_media_id": payload.cover_media_id or None,
        "gallery": list(dict.fromkeys(payload.gallery_media_ids)),
        "contact_name": (payload.contact_name or "").strip() or None,
        "contact_email": payload.contact_email,
        "contact_phone": (payload.contact_phone or "").strip() or None,
        "website": website,
    }
    if not fields["title"] or not fields["summary"]:
        raise _invalid("Название и краткое описание не могут быть пустыми")
    return fields, tag_names


def _apply_tags(db: Session, card: models.Card, names: list) -> None:
    existing = {}
    if names:
        existing = {t.name: t for t in db.query(models.Tag).filter(models.Tag.name.in_(names))}
    tags = []
    for name in names:
        tag = existing.get(name)
        if tag is None:
            tag = models.Tag(name=name)
            db.add(tag)
        tags.append(tag)
    card.tags = tags


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:  # два одновременных запроса создали один и тот же новый тег
        db.rollback()
        raise HTTPException(status_code=409, detail="Конфликт при сохранении, повторите запрос")


# ---------------------------------------------------------------- управление (сотрудники)
@router.get("/manage", response_model=List[schemas.CardBrief])
def list_manage(
    faculty_id: Optional[int] = None,
    status: Optional[schemas.CardStatus] = None,
    q: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_staff),
):
    """Рабочий список: администратор видит карточки своего факультета, суперадмин — все."""
    query = db.query(models.Card).options(joinedload(models.Card.faculty))
    if user.role != "superuser":
        query = query.filter(models.Card.faculty_id == user.faculty_id)
    elif faculty_id:
        query = query.filter(models.Card.faculty_id == faculty_id)
    if status:
        query = query.filter(models.Card.status == status)
    if q:
        query = query.filter(models.Card.title.ilike(f"%{_like_escape(q)}%", escape="\\"))
    rows = query.order_by(models.Card.updated_at.desc(), models.Card.id.desc()).offset(skip).limit(limit).all()
    return [brief(c) for c in rows]


@router.get("/manage/stats", response_model=schemas.StaffStats)
def manage_stats(db: Session = Depends(get_db), user: models.User = Depends(auth.require_staff)):
    cards = db.query(models.Card)
    inquiries = db.query(models.Inquiry).join(models.Card, models.Card.id == models.Inquiry.card_id)
    if user.role != "superuser":
        cards = cards.filter(models.Card.faculty_id == user.faculty_id)
        inquiries = inquiries.filter(models.Card.faculty_id == user.faculty_id)
    total = cards.count()
    published = cards.filter(models.Card.status == "published").count()
    return schemas.StaffStats(
        cards_total=total,
        cards_published=published,
        cards_draft=total - published,
        inquiries_new=inquiries.filter(models.Inquiry.status == "new").count(),
    )


@router.post("", response_model=schemas.CardOut, status_code=201)
def create_card(
    payload: schemas.CardWrite,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_staff),
):
    fields, tag_names = _prepare(db, user, payload, current_faculty_id=None, existing_media=set())
    card = models.Card(author_id=user.id, **fields)
    card.published_at = datetime.utcnow() if fields["status"] == "published" else None
    db.add(card)
    db.flush()
    _apply_tags(db, card, tag_names)
    _commit(db)
    return detail(_load(db, card.id), user)


@router.put("/{card_id}", response_model=schemas.CardOut)
def update_card(
    card_id: int,
    payload: schemas.CardWrite,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_staff),
):
    card = _get_manageable(db, card_id, user)
    current_media = set(([card.cover_media_id] if card.cover_media_id else []) + list(card.gallery or []))
    fields, tag_names = _prepare(db, user, payload, card.faculty_id, current_media)

    was_published = card.status == "published"
    for key, value in fields.items():
        setattr(card, key, value)
    if fields["status"] == "published":
        if not was_published:
            card.published_at = datetime.utcnow()
    else:
        card.published_at = None
    _apply_tags(db, card, tag_names)
    _commit(db)
    return detail(_load(db, card.id), user)


@router.put("/{card_id}/status", response_model=schemas.CardOut)
def set_card_status(
    card_id: int,
    payload: schemas.CardStatusUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_staff),
):
    """Быстро опубликовать карточку или вернуть в черновики (без правки остальных полей)."""
    card = _get_manageable(db, card_id, user)
    if payload.status == "published" and card.status != "published":
        card.published_at = datetime.utcnow()
    elif payload.status != "published":
        card.published_at = None
    card.status = payload.status
    _commit(db)
    return detail(_load(db, card.id), user)


@router.delete("/{card_id}")
def delete_card(
    card_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_staff),
):
    card = _get_manageable(db, card_id, user)
    db.delete(card)  # заявки по карточке удаляются вместе с ней
    db.commit()
    return {"message": "Card deleted"}


# ---------------------------------------------------------------- публичные страницы
@router.get("", response_model=List[schemas.CardBrief])
def list_cards(
    q: Optional[str] = None,
    faculty_id: Optional[int] = None,
    tag: Optional[str] = None,
    readiness: Optional[schemas.Readiness] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Каталог: только опубликованные карточки. Поиск по словам с учётом окончаний
    (без нейросети — умный подбор по смыслу делает /ai-search/)."""
    query = (
        db.query(models.Card)
        .options(joinedload(models.Card.faculty))
        .filter(models.Card.status == "published")
    )
    if faculty_id:
        query = query.filter(models.Card.faculty_id == faculty_id)
    if readiness:
        query = query.filter(models.Card.readiness == readiness)
    cards = query.all()

    if tag:
        try:
            wanted = normalize_tag(tag)
        except ValueError:
            wanted = ""
        cards = [c for c in cards if any(t.name == wanted for t in c.tags)]

    if q and q.strip():
        by_id = {c.id: c for c in cards}
        ranked = rank([_search_doc(c) for c in cards], q, use_synonyms=False)
        cards = [by_id[doc.id] for doc, _ in ranked]
    else:
        cards.sort(key=lambda c: (c.published_at or datetime.min, c.id), reverse=True)

    return [brief(c) for c in cards[skip: skip + limit]]


@router.get("/{card_id}", response_model=schemas.CardOut)
def get_card(
    card_id: int,
    db: Session = Depends(get_db),
    user=Depends(auth.get_optional_user),
):
    card = _load(db, card_id)
    role = user.role if user else None
    faculty = user.faculty_id if user else None
    if card is None or not can_view_card(card.status, role, faculty, card.faculty_id):
        raise HTTPException(status_code=404, detail="Card not found")
    return detail(card, user)
