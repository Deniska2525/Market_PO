from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime

# ===== Auth schemas =====
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

# ===== User schemas =====
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    # ВАЖНО: здесь намеренно нет поля role.
    # Роль всегда выставляется сервером (см. routers/users.py -> register)
    # и меняется только через админский эндпоинт PUT /admin/users/{id}/role.
    # Максимум 72 символа — ограничение bcrypt.
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Пароль должен содержать и буквы, и цифры")
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None

class User(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    faculty_id: Optional[int] = None
    faculty_name: Optional[str] = None

    class Config:
        from_attributes = True


def _check_password_strength(value: str) -> str:
    if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
        raise ValueError("Пароль должен содержать и буквы, и цифры")
    return value


# ===== Администрирование пользователей (только суперадмин) =====
class FacultyAdminCreate(BaseModel):
    """Аккаунт администратора факультета. Факультет обязателен: админ без факультета
    не может работать ни с одной карточкой."""
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(default=None, max_length=150)
    password: str = Field(min_length=8, max_length=72)
    faculty_id: int

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _check_password_strength(v)


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=150)
    email: Optional[EmailStr] = None
    role: Optional[Literal["user", "admin"]] = None
    faculty_id: Optional[int] = None
    is_active: Optional[bool] = None
    new_password: Optional[str] = Field(default=None, min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        return None if v is None else _check_password_strength(v)


class AdminStats(BaseModel):
    faculties: int
    cards_total: int
    cards_published: int
    inquiries_new: int
    users_total: int
    admins_total: int


class StaffStats(BaseModel):
    cards_total: int
    cards_published: int
    cards_draft: int
    inquiries_new: int


# ===== Факультеты и теги =====
class FacultyWrite(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    short_name: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = Field(default=None, max_length=2000)


class FacultyOut(BaseModel):
    id: int
    name: str
    short_name: Optional[str] = None
    description: Optional[str] = None
    cards_count: int = 0  # опубликованных карточек
    created_at: Optional[datetime] = None


class TagOut(BaseModel):
    id: int
    name: str
    count: int = 0


# ===== Карточки =====
CardStatus = Literal["draft", "published"]
Readiness = Literal["idea", "prototype", "pilot", "ready"]


class CardWrite(BaseModel):
    """Создание и полная замена карточки. faculty_id нужен только суперадмину:
    администратор факультета всегда работает со своим."""
    faculty_id: Optional[int] = None
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=20000)
    status: CardStatus = "draft"
    readiness: Optional[Readiness] = None
    cover_media_id: Optional[int] = None
    gallery_media_ids: List[int] = Field(default_factory=list, max_length=6)
    tags: List[str] = Field(default_factory=list, max_length=20)
    contact_name: Optional[str] = Field(default=None, max_length=100)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(default=None, max_length=30)
    website: Optional[str] = Field(default=None, max_length=500)


class CardStatusUpdate(BaseModel):
    status: CardStatus


class CardBrief(BaseModel):
    id: int
    title: str
    summary: str
    faculty_id: int
    faculty_name: str
    faculty_short_name: Optional[str] = None
    status: str
    readiness: Optional[str] = None
    cover_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CardOut(CardBrief):
    description: Optional[str] = None  # HTML, уже очищен сервером
    gallery_urls: List[str] = Field(default_factory=list)
    cover_media_id: Optional[int] = None
    gallery_media_ids: List[int] = Field(default_factory=list)
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    created_at: Optional[datetime] = None
    can_manage: bool = False


# ===== Заявки =====
class InquiryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=30)
    organization: Optional[str] = Field(default=None, max_length=150)
    message: str = Field(min_length=5, max_length=2000)
    # Ловушка для ботов: поле скрыто от людей, и если оно заполнено, заявка отбрасывается
    website: Optional[str] = Field(default=None, max_length=200)


class InquiryOut(BaseModel):
    id: int
    card_id: int
    card_title: str
    faculty_id: int
    name: str
    email: str
    phone: Optional[str] = None
    organization: Optional[str] = None
    message: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class InquiryStatusUpdate(BaseModel):
    status: Literal["new", "in_progress", "done"]


# ===== Поиск =====
class AISearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class AISearchItem(BaseModel):
    card: CardBrief
    reason: str = ""


class AISearchResponse(BaseModel):
    mode: Literal["ai", "keywords"]  # ai — подбор нейросетью, keywords — запасной поиск по словам
    message: str = ""
    results: List[AISearchItem] = Field(default_factory=list)
    terms: List[str] = Field(default_factory=list)  # какие понятия искали


# ===== Медиатека =====
class MediaOut(BaseModel):
    id: int
    kind: str
    filename: str
    mime_type: str
    size: int = 0
    url: Optional[str] = None  # только у изображений
    owner_id: Optional[int] = None
    created_at: Optional[datetime] = None
