# -*- coding: utf-8 -*-
"""Теги. Публичный список — только теги опубликованных карточек (с числом карточек).
Удалять теги может суперадмин (тег снимается со всех карточек)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=List[schemas.TagOut])
def list_tags(
    faculty_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = (
        db.query(models.Tag.id, models.Tag.name, func.count(models.Card.id))
        .join(models.card_tags, models.card_tags.c.tag_id == models.Tag.id)
        .join(models.Card, models.Card.id == models.card_tags.c.card_id)
        .filter(models.Card.status == "published")
    )
    if faculty_id:
        query = query.filter(models.Card.faculty_id == faculty_id)
    rows = (
        query.group_by(models.Tag.id, models.Tag.name)
        .order_by(func.count(models.Card.id).desc(), models.Tag.name)
        .limit(limit)
        .all()
    )
    return [schemas.TagOut(id=tag_id, name=name, count=count) for tag_id, name, count in rows]


@router.delete("/{tag_id}")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.check_superuser),
):
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.execute(models.card_tags.delete().where(models.card_tags.c.tag_id == tag_id))
    db.delete(tag)
    db.commit()
    return {"message": "Tag deleted"}
