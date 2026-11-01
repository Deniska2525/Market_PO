# -*- coding: utf-8 -*-
"""Факультеты. Читать может любой, создавать, править и удалять — только суперадмин."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db

router = APIRouter(prefix="/faculties", tags=["faculties"])


def _published_counts(db: Session) -> dict:
    rows = (
        db.query(models.Card.faculty_id, func.count(models.Card.id))
        .filter(models.Card.status == "published")
        .group_by(models.Card.faculty_id)
        .all()
    )
    return {faculty_id: count for faculty_id, count in rows}


def _out(faculty: models.Faculty, counts: dict) -> schemas.FacultyOut:
    return schemas.FacultyOut(
        id=faculty.id,
        name=faculty.name,
        short_name=faculty.short_name,
        description=faculty.description,
        cards_count=counts.get(faculty.id, 0),
        created_at=faculty.created_at,
    )


def _get_or_404(db: Session, faculty_id: int) -> models.Faculty:
    faculty = db.query(models.Faculty).filter(models.Faculty.id == faculty_id).first()
    if faculty is None:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return faculty


def _name_taken(db: Session, name: str, exclude_id=None) -> bool:
    query = db.query(models.Faculty.id).filter(func.lower(models.Faculty.name) == name.lower())
    if exclude_id is not None:
        query = query.filter(models.Faculty.id != exclude_id)
    return query.first() is not None


@router.get("", response_model=List[schemas.FacultyOut])
def list_faculties(db: Session = Depends(get_db)):
    counts = _published_counts(db)
    return [_out(f, counts) for f in db.query(models.Faculty).order_by(models.Faculty.name)]


@router.get("/{faculty_id}", response_model=schemas.FacultyOut)
def get_faculty(faculty_id: int, db: Session = Depends(get_db)):
    return _out(_get_or_404(db, faculty_id), _published_counts(db))


@router.post("", response_model=schemas.FacultyOut, status_code=201)
def create_faculty(
    payload: schemas.FacultyWrite,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.check_superuser),
):
    name = payload.name.strip()
    if _name_taken(db, name):
        raise HTTPException(status_code=409, detail="Факультет с таким названием уже есть")
    faculty = models.Faculty(
        name=name,
        short_name=(payload.short_name or "").strip() or None,
        description=(payload.description or "").strip() or None,
    )
    db.add(faculty)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Факультет с таким названием уже есть")
    db.refresh(faculty)
    return _out(faculty, {})


@router.put("/{faculty_id}", response_model=schemas.FacultyOut)
def update_faculty(
    faculty_id: int,
    payload: schemas.FacultyWrite,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.check_superuser),
):
    faculty = _get_or_404(db, faculty_id)
    name = payload.name.strip()
    if _name_taken(db, name, exclude_id=faculty.id):
        raise HTTPException(status_code=409, detail="Факультет с таким названием уже есть")
    faculty.name = name
    faculty.short_name = (payload.short_name or "").strip() or None
    faculty.description = (payload.description or "").strip() or None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Факультет с таким названием уже есть")
    db.refresh(faculty)
    return _out(faculty, _published_counts(db))


@router.delete("/{faculty_id}")
def delete_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.check_superuser),
):
    faculty = _get_or_404(db, faculty_id)
    if db.query(models.Card.id).filter(models.Card.faculty_id == faculty.id).first():
        raise HTTPException(status_code=409, detail="К факультету привязаны карточки — сначала удалите или перенесите их")
    if db.query(models.User.id).filter(models.User.faculty_id == faculty.id).first():
        raise HTTPException(status_code=409, detail="К факультету привязаны администраторы — сначала смените им факультет")
    db.delete(faculty)
    db.commit()
    return {"message": "Faculty deleted"}
