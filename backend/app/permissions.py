# -*- coding: utf-8 -*-
"""Права доступа по ролям и факультетам. Только стандартная библиотека.

Роли:
  * superuser — суперадмин вуза: управляет факультетами, пользователями и любыми карточками;
  * admin     — администратор факультета: работает только с карточками СВОЕГО факультета;
  * user      — обычный пользователь: смотрит каталог и оставляет заявки.

Факультет админу назначает суперадмин при создании его аккаунта (см. routers/admin.py).
Все проверки делаются на сервере: интерфейс лишь прячет лишнее.
"""

SUPERUSER = "superuser"
ADMIN = "admin"
STAFF_ROLES = (ADMIN, SUPERUSER)


class FacultyAccessError(PermissionError):
    """Действие выходит за пределы факультета пользователя."""


def is_superuser(role) -> bool:
    return role == SUPERUSER


def can_manage_faculty(role, user_faculty_id, target_faculty_id) -> bool:
    """Может ли пользователь работать с материалами указанного факультета."""
    if role == SUPERUSER:
        return True
    return role == ADMIN and user_faculty_id is not None and user_faculty_id == target_faculty_id


def can_view_card(status, role, user_faculty_id, card_faculty_id) -> bool:
    """Опубликованное видят все; черновики — суперадмин и админ того же факультета."""
    return status == "published" or can_manage_faculty(role, user_faculty_id, card_faculty_id)


def resolve_card_faculty(role, user_faculty_id, requested_faculty_id):
    """Факультет новой или изменяемой карточки.

    Суперадмин выбирает факультет сам (None — значит, не указан). Админ всегда работает
    со своим факультетом: если в запросе указан другой — это отказ, а не молчаливая подмена.
    """
    if role == SUPERUSER:
        return requested_faculty_id
    if role == ADMIN and user_faculty_id is not None:
        if requested_faculty_id not in (None, user_faculty_id):
            raise FacultyAccessError("Можно работать только с карточками своего факультета")
        return user_faculty_id
    raise FacultyAccessError("Недостаточно прав")
