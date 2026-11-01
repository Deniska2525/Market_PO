# -*- coding: utf-8 -*-
"""Заявки на сотрудничество. Оставить заявку может любой посетитель; видят и обрабатывают
её администратор факультета карточки и суперадмин."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db
from ..permissions import can_manage_faculty
from ..rate_limit import limiter

router = APIRouter(tags=["inquiries"])


def _out(inquiry: models.Inquiry) -> schemas.InquiryOut:
    return schemas.InquiryOut(
        id=inquiry.id,
        card_id=inquiry.card_id,
        card_title=inquiry.card.title,
        faculty_id=inquiry.card.faculty_id,
        name=inquiry.name,
        email=inquiry.email,
        phone=inquiry.phone,
        organization=inquiry.organization,
        message=inquiry.message,
        status=inquiry.status,
        created_at=inquiry.created_at,
        updated_at=inquiry.updated_at,
    )


@router.post("/cards/{card_id}/inquiries", status_code=201)
@limiter.limit("5/hour")
def create_inquiry(
    request: Request,
    card_id: int,
    payload: schemas.InquiryCreate,
    db: Session = Depends(get_db),
    user=Depends(auth.get_optional_user),
):
    card = (
        db.query(models.Card)
        .filter(models.Card.id == card_id, models.Card.status == "published")
        .first()
    )
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")

    # Ловушка для ботов: человек скрытого поля не видит и не заполняет.
    # Ответ тот же, что при успехе, чтобы бот не понял, что его отсеяли.
    if payload.website:
        return {"message": "Заявка отправлена"}

    db.add(models.Inquiry(
        card_id=card.id,
        name=payload.name.strip(),
        email=payload.email,
        phone=(payload.phone or "").strip() or None,
        organization=(payload.organization or "").strip() or None,
        message=payload.message.strip(),
        user_id=user.id if user else None,
    ))
    db.commit()
    return {"message": "Заявка отправлена"}


def _get_manageable(db: Session, inquiry_id: int, user: models.User) -> models.Inquiry:
    inquiry = db.query(models.Inquiry).filter(models.Inquiry.id == inquiry_id).first()
    if inquiry is None or not can_manage_faculty(user.role, user.faculty_id, inquiry.card.faculty_id):
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return inquiry


@router.get("/inquiries", response_model=List[schemas.InquiryOut])
def list_inquiries(
    status: Optional[str] = Query(None, pattern="^(new|in_progress|done)$"),
    faculty_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_staff),
):
    query = db.query(models.Inquiry).join(models.Card, models.Card.id == models.Inquiry.card_id)
    if user.role != "superuser":
        query = query.filter(models.Card.faculty_id == user.faculty_id)
    elif faculty_id:
        query = query.filter(models.Card.faculty_id == faculty_id)
    if status:
        query = query.filter(models.Inquiry.status == status)
    rows = query.order_by(models.Inquiry.created_at.desc(), models.Inquiry.id.desc()).offset(skip).limit(limit).all()
    return [_out(i) for i in rows]


@router.put("/inquiries/{inquiry_id}/status", response_model=schemas.InquiryOut)
def set_inquiry_status(
    inquiry_id: int,
    payload: schemas.InquiryStatusUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_staff),
):
    inquiry = _get_manageable(db, inquiry_id, user)
    inquiry.status = payload.status
    db.commit()
    db.refresh(inquiry)
    return _out(inquiry)


@router.delete("/inquiries/{inquiry_id}")
def delete_inquiry(
    inquiry_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.require_staff),
):
    inquiry = _get_manageable(db, inquiry_id, user)
    db.delete(inquiry)
    db.commit()
    return {"message": "Inquiry deleted"}
