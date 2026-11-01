# -*- coding: utf-8 -*-
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, ForeignKey, DateTime, JSON, Table,
    BigInteger, LargeBinary,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, deferred
from datetime import datetime
from .database import Base

# На PostgreSQL храним как JSONB, на остальных СУБД — как обычный JSON
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Faculty(Base):
    """Факультет вуза: создаёт суперадмин. К нему привязаны карточки и администраторы."""
    __tablename__ = "faculties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    short_name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cards = relationship("Card", back_populates="faculty")
    users = relationship("User", back_populates="faculty")


class User(Base):
    """Роли: superuser (суперадмин вуза), admin (администратор факультета; обязательно
    с faculty_id), user (обычный пользователь)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    # Факультет администратора. Назначает суперадмин при создании аккаунта
    faculty_id = Column(Integer, ForeignKey("faculties.id"), nullable=True, index=True)

    faculty = relationship("Faculty", back_populates="users")

    @property
    def faculty_name(self):
        return self.faculty.name if self.faculty else None


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    # Храним только SHA-256 от токена — сырой токен есть только у клиента
    token_hash = Column(String, unique=True, index=True)
    expires_at = Column(DateTime)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


# Связь «карточка — тег» (многие ко многим)
card_tags = Table(
    "card_tags",
    Base.metadata,
    Column("card_id", Integer, ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    """Тег — справочник: одно и то же слово хранится один раз, в нижнем регистре."""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)


class Card(Base):
    """Карточка: разработка, проект или технология вуза. Принадлежит одному факультету."""
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    faculty_id = Column(Integer, ForeignKey("faculties.id"), nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    summary = Column(String, nullable=False)  # короткое описание для списков и поиска
    description = Column(Text, nullable=True)  # HTML из редактора, очищается при сохранении
    status = Column(String, default="draft", index=True)  # draft | published
    readiness = Column(String, nullable=True)  # idea | prototype | pilot | ready
    cover_media_id = Column(Integer, nullable=True)  # файл из медиатеки (изображение)
    gallery = Column(JSONType, nullable=False, default=list)  # id изображений из медиатеки
    contact_name = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

    faculty = relationship("Faculty", back_populates="cards")
    author = relationship("User")
    tags = relationship("Tag", secondary=card_tags, lazy="selectin")
    inquiries = relationship("Inquiry", back_populates="card", cascade="all, delete-orphan")


class Inquiry(Base):
    """Заявка посетителя на сотрудничество по карточке. Видят администратор факультета
    карточки и суперадмин."""
    __tablename__ = "inquiries"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String, default="new", index=True)  # new | in_progress | done
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # если автор заявки вошёл в систему
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    card = relationship("Card", back_populates="inquiries")


class MediaFile(Base):
    """Файл медиатеки: изображение карточки (публичное) или файл. На диске лежит под
    сгенерированным именем stored_name — имя от пользователя в путь не попадает."""
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String, nullable=False, index=True)  # image | file
    filename = Column(String, nullable=False)  # очищенное исходное имя, только для показа
    stored_name = Column(String, unique=True, nullable=False)
    mime_type = Column(String, nullable=False)
    size = Column(BigInteger, default=0)
    sha256 = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Содержимое изображения при MEDIA_STORAGE=db (иначе файл лежит на диске). deferred: в списках
    # файлов содержимое не загружается, только при выдаче самой картинки
    data = deferred(Column(LargeBinary, nullable=True))
