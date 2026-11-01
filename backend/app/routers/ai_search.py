import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..ai_search import ai_available, ai_search, keyword_search
from ..database import get_db
from ..rate_limit import limiter
from .cards import brief

logger = logging.getLogger("ai_search")
router = APIRouter(prefix="/ai-search", tags=["ai-search"])

FALLBACK_NOTE = "Нейросеть сейчас недоступна, поэтому показан поиск по ключевым словам и связанным темам."


@router.post("/", response_model=schemas.AISearchResponse)
@limiter.limit("10/minute")  # запрос к нейросети стоит денег или квоты — защищаем ключ от злоупотреблений
def ai_search_endpoint(request: Request, payload: schemas.AISearchRequest, db: Session = Depends(get_db)):
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Пустой запрос")

    mode = "ai"
    result = None
    if ai_available():
        try:
            result = ai_search(query, db)
        except Exception:
            # Сбой провайдера не должен оставлять человека без результата — идём в запасной режим
            logger.exception("Ошибка ИИ-поиска для запроса: %s", query)

    if result is None:
        mode = "keywords"
        result = keyword_search(query, db)
        if ai_available():
            result["message"] = FALLBACK_NOTE + " " + result["message"]

    # Карточки сверяем с базой одним запросом: неизвестные и неопубликованные отбрасываются
    wanted = [item["card_id"] for item in result.get("results", [])]
    cards = {}
    if wanted:
        rows = (
            db.query(models.Card)
            .options(joinedload(models.Card.faculty))
            .filter(models.Card.id.in_(wanted), models.Card.status == "published")
            .all()
        )
        cards = {c.id: c for c in rows}

    items = [
        {"card": brief(cards[item["card_id"]]), "reason": item.get("reason", "")}
        for item in result.get("results", [])
        if item["card_id"] in cards
    ]
    return {
        "mode": mode,
        "message": result.get("message", ""),
        "results": items,
        "terms": result.get("terms", []),
    }
