# -*- coding: utf-8 -*-
"""Администрирование (только суперадмин): статистика и пользователи.

Администраторов факультетов создаёт суперадмин: он же назначает им факультет. Публичная
регистрация даёт только роль «user» — выбрать себе роль или факультет там нельзя.
"""
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from .. import auth, models, schemas
from ..database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


def _invalid(message: str) -> HTTPException:
    return HTTPException(status_code=422, detail=message)


def _faculty_exists(db: Session, faculty_id: int) -> bool:
    return db.query(models.Faculty.id).filter(models.Faculty.id == faculty_id).first() is not None


@router.get("/stats", response_model=schemas.AdminStats)
def get_stats(db: Session = Depends(get_db), admin: models.User = Depends(auth.check_superuser)):
    return schemas.AdminStats(
        faculties=db.query(models.Faculty).count(),
        cards_total=db.query(models.Card).count(),
        cards_published=db.query(models.Card).filter(models.Card.status == "published").count(),
        inquiries_new=db.query(models.Inquiry).filter(models.Inquiry.status == "new").count(),
        users_total=db.query(models.User).count(),
        admins_total=db.query(models.User).filter(models.User.role == "admin").count(),
    )


@router.get("/users", response_model=List[schemas.User])
def list_users(
    role: Optional[Literal["user", "admin", "superuser"]] = None,
    faculty_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.check_superuser),
):
    query = db.query(models.User).options(joinedload(models.User.faculty))
    if role:
        query = query.filter(models.User.role == role)
    if faculty_id:
        query = query.filter(models.User.faculty_id == faculty_id)
    if search:
        pattern = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.filter(
            models.User.username.ilike(pattern, escape="\\")
            | models.User.email.ilike(pattern, escape="\\")
            | models.User.full_name.ilike(pattern, escape="\\")
        )
    return query.order_by(models.User.id.desc()).offset(skip).limit(limit).all()


@router.post("/users", response_model=schemas.User, status_code=201)
def create_faculty_admin(
    payload: schemas.FacultyAdminCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.check_superuser),
):
    """Создаёт администратора факультета. Факультет назначается сразу и обязательно."""
    if not _faculty_exists(db, payload.faculty_id):
        raise _invalid("Факультет не найден")
    taken = db.query(models.User).filter(
        (models.User.username == payload.username) | (models.User.email == payload.email)
    ).first()
    if taken:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    user = models.User(
        username=payload.username,
        email=payload.email,
        hashed_password=auth.get_password_hash(payload.password),
        full_name=(payload.full_name or "").strip() or None,
        role="admin",
        faculty_id=payload.faculty_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    payload: schemas.AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.check_superuser),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "superuser":
        raise HTTPException(status_code=403, detail="Аккаунт суперадмина изменять нельзя")

    updates = payload.model_dump(exclude_unset=True)

    new_role = updates.get("role", user.role)
    new_faculty = updates["faculty_id"] if "faculty_id" in updates else user.faculty_id
    if new_role == "admin":
        if new_faculty is None:
            raise _invalid("Для администратора нужно выбрать факультет")
        if not _faculty_exists(db, new_faculty):
            raise _invalid("Факультет не найден")
    else:
        new_faculty = None  # у обычного пользователя факультета нет

    if updates.get("email") and updates["email"] != user.email:
        if db.query(models.User.id).filter(models.User.email == updates["email"], models.User.id != user.id).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = updates["email"]

    if "full_name" in updates:
        user.full_name = (updates["full_name"] or "").strip() or None
    if "is_active" in updates and updates["is_active"] is not None:
        user.is_active = updates["is_active"]
    user.role = new_role
    user.faculty_id = new_faculty

    # Деактивация и смена пароля завершают все сессии пользователя
    if updates.get("is_active") is False or updates.get("new_password"):
        if updates.get("new_password"):
            user.hashed_password = auth.get_password_hash(updates["new_password"])
        auth.revoke_all_user_tokens(db, user.id)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.check_superuser),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "superuser":
        raise HTTPException(status_code=403, detail="Cannot delete superuser")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    # Карточки, заявки и файлы остаются, только теряют привязку к удаляемому аккаунту
    db.query(models.Card).filter(models.Card.author_id == user.id).update({"author_id": None})
    db.query(models.Inquiry).filter(models.Inquiry.user_id == user.id).update({"user_id": None})
    db.query(models.MediaFile).filter(models.MediaFile.owner_id == user.id).update({"owner_id": None})
    db.query(models.RefreshToken).filter(models.RefreshToken.user_id == user.id).delete()
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}
