"""
MCP-сервер каталога разработок вуза.

Выставляет каталог как MCP-инструменты, чтобы сторонние ИИ-агенты (Claude Desktop и другие
MCP-хосты) могли искать разработки напрямую. Это отдельная от app/ai_search.py вещь:
  - app/ai_search.py сам ходит во внешнюю нейросеть, чтобы обслужить поиск на нашем сайте;
  - mcp_tools.py только отдаёт данные по протоколу MCP, а вызывающая сторона сама выбирает модель.

Транспорт: Streamable HTTP, stateless. Подключение: добавить коннектор с URL
`https://<домен-бэкенда>/mcp`. Доступ публичный, только чтение опубликованных карточек
(то же, что видит любой посетитель сайта).
"""
from typing import Optional

from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import joinedload

from . import models
from .database import SessionLocal
from .search import SearchDoc, html_to_text, rank

mcp = FastMCP(
    "university-showcase",
    instructions=(
        "Каталог разработок, проектов и технологий вуза по факультетам. Используй "
        "search_cards, чтобы найти разработки под задачу пользователя (запрос можно "
        "формулировать широко: поиск учитывает связанные темы), list_faculties, чтобы "
        "узнать факультеты, и get_card, чтобы получить карточку целиком."
    ),
    # streamable_http_app() сам монтирует обработчик на «/mcp»; чтобы после монтирования
    # в main.py путь остался «/mcp», а не «/mcp/mcp», задаём внутренний путь «/»
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
)


def _published(db):
    return (
        db.query(models.Card)
        .options(joinedload(models.Card.faculty))
        .filter(models.Card.status == "published")
    )


@mcp.tool()
def search_cards(query: str, faculty: Optional[str] = None, limit: int = 10) -> list[dict]:
    """Ищет опубликованные разработки вуза по описанию потребности.

    query — запрос обычными словами; faculty — часть названия факультета (необязательно).
    """
    db = SessionLocal()
    try:
        wanted = (faculty or "").strip().lower()
        docs = [
            SearchDoc(c.id, c.title, c.summary, html_to_text(c.description), [t.name for t in c.tags], c.faculty.name)
            for c in _published(db).all()
            if not wanted or wanted in c.faculty.name.lower()
        ]
        ranked = rank(docs, query, use_synonyms=True, limit=max(1, min(limit, 30)))
        return [
            {"id": d.id, "title": d.title, "summary": d.summary, "faculty": d.faculty, "tags": d.tags}
            for d, _ in ranked
        ]
    finally:
        db.close()


@mcp.tool()
def list_faculties() -> list[dict]:
    """Возвращает факультеты и число опубликованных карточек у каждого."""
    db = SessionLocal()
    try:
        counts = {}
        for card in _published(db).all():
            counts[card.faculty_id] = counts.get(card.faculty_id, 0) + 1
        return [
            {"id": f.id, "name": f.name, "short_name": f.short_name, "cards": counts.get(f.id, 0)}
            for f in db.query(models.Faculty).order_by(models.Faculty.name)
        ]
    finally:
        db.close()


@mcp.tool()
def get_card(card_id: int) -> dict:
    """Возвращает опубликованную карточку целиком по её id."""
    db = SessionLocal()
    try:
        card = _published(db).filter(models.Card.id == card_id).first()
        if card is None:
            return {"error": f"Карточка с id={card_id} не найдена"}
        return {
            "id": card.id,
            "title": card.title,
            "summary": card.summary,
            "description": html_to_text(card.description),
            "faculty": card.faculty.name,
            "tags": [t.name for t in card.tags],
            "readiness": card.readiness,
            "contact_name": card.contact_name,
            "contact_email": card.contact_email,
            "website": card.website,
        }
    finally:
        db.close()
