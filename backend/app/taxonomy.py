# -*- coding: utf-8 -*-
"""Теги карточек: нормализация и проверка. Только стандартная библиотека."""
import re

MAX_TAGS_PER_CARD = 10
MAX_TAG_LENGTH = 40
_ALLOWED = re.compile(r"^[\w\s\-+#./]+$", re.UNICODE)


def normalize_tag(name) -> str:
    """«  Компьютерное   Зрение » -> «компьютерное зрение». Пустая строка — нечего сохранять."""
    text = re.sub(r"\s+", " ", str(name or "")).strip().lower().replace("ё", "е")
    if not text:
        return ""
    if len(text) > MAX_TAG_LENGTH:
        raise ValueError(f"тег «{text[:20]}…» длиннее {MAX_TAG_LENGTH} символов")
    if not _ALLOWED.match(text):
        raise ValueError(f"в теге «{text}» недопустимые символы")
    return text


def normalize_tags(names) -> list:
    """Список тегов без пустых и повторов, порядок сохраняется."""
    result = []
    for name in names or []:
        tag = normalize_tag(name)
        if tag and tag not in result:
            result.append(tag)
    if len(result) > MAX_TAGS_PER_CARD:
        raise ValueError(f"максимум {MAX_TAGS_PER_CARD} тегов у одной карточки")
    return result
