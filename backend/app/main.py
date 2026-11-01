import os
from contextlib import asynccontextmanager, AsyncExitStack
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .rate_limit import limiter
from .database import engine, Base, SessionLocal
from .schema_sync import sync_schema
from . import university_seed
from .routers import users, admin, faculties, tags, cards, inquiries, ai_search, media
from . import models  # noqa: F401  (регистрирует таблицы в Base до create_all)
from .mcp_tools import mcp

# Создаём таблицы, если их ещё нет. НЕ удаляет и не трогает существующие данные.
Base.metadata.create_all(bind=engine)

# Безопасно добавляем недостающие КОЛОНКИ в уже существующие таблицы (create_all этого
# не делает — см. schema_sync.py). Так, например, у пользователей из прежней базы
# появляется колонка faculty_id.
sync_schema(engine, Base)

# Факультеты, демо-карточки и демо-аккаунты при первом запуске (см. university_seed.py).
# Идемпотентно: на заполненной базе ничего не дублирует.
_seed_db = SessionLocal()
try:
    university_seed.run(_seed_db)
finally:
    _seed_db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ВАЖНО: у FastMCP свой session manager, который обязательно нужно запустить через
    # контекст-менеджер приложения — иначе MCP-эндпоинт отвечает ошибкой
    # "Task group is not initialized" на каждый запрос.
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield


app = FastAPI(title="University Showcase API", lifespan=lifespan)

# Rate limiting (slowapi): вход, регистрация, заявки и ИИ-поиск (см. rate_limit.py)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# CORS: явные списки методов и заголовков вместо "*" — с allow_credentials=True
# лучше не давать шире, чем нужно
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost",
        FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(users.router)
app.include_router(admin.router)
app.include_router(faculties.router)
app.include_router(tags.router)
app.include_router(cards.router)
app.include_router(inquiries.router)
app.include_router(ai_search.router)
app.include_router(media.router)

# MCP-сервер каталога доступен по /mcp внешним ИИ-агентам (Claude Desktop и т.п.).
# Публичный, только чтение опубликованных карточек.
app.mount("/mcp", mcp.streamable_http_app())

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return {"message": "University Showcase API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
