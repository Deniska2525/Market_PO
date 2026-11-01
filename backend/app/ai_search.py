"""
Контекстный поиск по карточкам разработок вуза.

Задача: человек описывает СВОЮ ПОТРЕБНОСТЬ обычными словами («нужен робот для склада»),
а нужная разработка может называться совсем иначе («компьютерное зрение» на факультете
кибернетики). Обычный поиск по словам её не найдёт. Нейросеть:
  1. понимает, какие области науки и техники могут закрыть потребность, в том числе
     неочевидные (робот -> компьютерное зрение, навигация, сенсоры);
  2. несколько раз вызывает инструмент search_cards с разными формулировками;
  3. отбирает из найденного лучшие карточки и объясняет, почему каждая подходит;
  4. ничего не выдумывает: роутер сверяет id карточек с базой и отбрасывает неизвестные
     и неопубликованные.

Если ключ нейросети не задан или провайдер недоступен, работает запасной режим
keyword_search(): поиск по словам с учётом окончаний и словарём связанных понятий
(app/search.py). Он слабее нейросети, но не требует внешних сервисов.

Провайдер — любой OpenAI-совместимый (OpenRouter, Groq, Gemini): достаточно поменять
AI_BASE_URL, AI_MODEL и AI_API_KEY. По умолчанию — OpenRouter и бесплатная Gemma 4,
ключ: https://openrouter.ai/keys
"""
import json
import logging
import os

from openai import APIError, OpenAI
from sqlalchemy.orm import Session, joinedload

from . import models
from .search import SearchDoc, expand_query, html_to_text, matching_tags, rank, tokenize

logger = logging.getLogger("ai_search")

AI_BASE_URL = os.getenv("AI_BASE_URL", "https://openrouter.ai/api/v1")
AI_MODEL = os.getenv("AI_MODEL", "google/gemma-4-31b-it:free")
MAX_TOOL_ITERATIONS = 5
MAX_RESULTS = 6
TOOL_RESULTS_LIMIT = 10
CONTEXT_TAGS_LIMIT = 80

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_cards",
        "description": (
            "Ищет опубликованные карточки разработок вуза по ключевым словам (название, "
            "краткое описание, теги, текст). Вызывай несколько раз с РАЗНЫМИ формулировками: "
            "сам запрос пользователя, связанные технологии, смежные области, синонимы."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Слова через пробел, например: 'компьютерное зрение распознавание'",
                },
                "faculty": {
                    "type": "string",
                    "description": "Часть названия факультета, чтобы искать только в нём (необязательно)",
                },
            },
            "required": ["keywords"],
        },
    },
}

SYSTEM_PROMPT = """Ты помогаешь подбирать университетские разработки под потребности людей и компаний.
В каталоге карточки разработок, проектов и технологий вуза; каждая принадлежит факультету и
имеет теги. Человек описывает, что ему нужно, своими словами. Нужная разработка может называться
совсем иначе, чем он сформулировал запрос: например, человеку нужен робот, а на факультете
кибернетики есть разработка по компьютерному зрению, без которой робот не увидит окружающий мир.

Как действовать:
1. Пойми потребность: какую задачу человек решает, какие технологии и области науки могут её закрыть,
   включая неочевидные и смежные.
2. Вызови search_cards минимум один раз и лучше несколько раз с разными формулировками: сам запрос,
   связанные технологии, смежные области. Ориентируйся на факультеты и теги каталога из списка ниже.
3. Выбери из найденного не больше шести самых подходящих карточек, по убыванию пользы для человека.
   Для каждой коротко объясни (1-2 предложения), что это за разработка и почему она подходит,
   с упоминанием факультета.
4. Не выдумывай карточки и id: используй только те, что вернул инструмент.
5. Если ничего подходящего нет, честно скажи об этом и верни пустой список results.
6. В конце ответь ТОЛЬКО валидным JSON без markdown и пояснений вокруг, строго в формате:
   {
     "message": "1-2 предложения: как ты понял потребность и что нашлось",
     "terms": ["понятия, по которым ты искал", "..."],
     "results": [{"card_id": <id из результатов инструмента>, "reason": "почему подходит"}]
   }
"""


def ai_available() -> bool:
    return bool(os.getenv("AI_API_KEY"))


def _published_docs(db: Session) -> list:
    cards = (
        db.query(models.Card)
        .options(joinedload(models.Card.faculty))
        .filter(models.Card.status == "published")
        .all()
    )
    return [
        SearchDoc(
            id=c.id,
            title=c.title,
            summary=c.summary,
            text=html_to_text(c.description),
            tags=[t.name for t in c.tags],
            faculty=c.faculty.name,
        )
        for c in cards
    ]


def _catalog_context(docs: list) -> str:
    """Факультеты и самые частые теги каталога: нейросеть видит словарь предметной области
    и подбирает формулировки поиска под реальные теги."""
    faculties = sorted({d.faculty for d in docs})
    counts = {}
    for doc in docs:
        for tag in doc.tags:
            counts[tag] = counts.get(tag, 0) + 1
    tags = [t for t, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:CONTEXT_TAGS_LIMIT]]
    return (
        "\n\nФакультеты каталога: " + (", ".join(faculties) or "—")
        + "\nТеги каталога: " + (", ".join(tags) or "—")
    )


def _run_tool(docs: list, args: dict) -> list:
    keywords = str(args.get("keywords") or "")
    faculty = str(args.get("faculty") or "").strip().lower()
    pool = [d for d in docs if not faculty or faculty in d.faculty.lower()]
    # Расширение запроса делает сама нейросеть, поэтому словарь связанных понятий здесь не нужен
    ranked = rank(pool, keywords, use_synonyms=False, limit=TOOL_RESULTS_LIMIT)
    return [
        {"id": d.id, "title": d.title, "summary": d.summary, "faculty": d.faculty, "tags": d.tags}
        for d, _ in ranked
    ]


def _empty(message: str) -> dict:
    return {"message": message, "terms": [], "results": []}


def _parse_final_json(raw: str) -> dict:
    text = (raw or "").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, AttributeError):
        # Модель ответила не JSON-ом — показываем её текст, но без карточек
        return _empty(text or "Не удалось разобрать ответ нейросети.")
    if not isinstance(parsed, dict):
        return _empty(text)

    results = []
    for item in parsed.get("results") or []:
        if isinstance(item, dict) and "card_id" in item:
            try:
                results.append({"card_id": int(item["card_id"]), "reason": str(item.get("reason", ""))})
            except (TypeError, ValueError):
                continue
    terms = [str(t) for t in (parsed.get("terms") or []) if isinstance(t, (str, int))]
    return {"message": str(parsed.get("message", "")), "terms": terms[:12], "results": results[:MAX_RESULTS]}


def ai_search(query: str, db: Session) -> dict:
    """Подбор нейросетью. Бросает RuntimeError без ключа и APIError при сбое провайдера:
    роутер в этих случаях переключается на keyword_search()."""
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        raise RuntimeError("AI_API_KEY не задана")

    docs = _published_docs(db)
    client = OpenAI(api_key=api_key, base_url=AI_BASE_URL)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + _catalog_context(docs)},
        {"role": "user", "content": query},
    ]

    for _ in range(MAX_TOOL_ITERATIONS):
        try:
            response = client.chat.completions.create(
                model=AI_MODEL,
                messages=messages,
                tools=[SEARCH_TOOL],
                tool_choice="auto",
                max_tokens=2048,
            )
        except APIError as exc:
            # В логах видна точная причина: 401 — неверный ключ, 429 — исчерпан лимит и т.д.
            logger.error("Ошибка обращения к AI-провайдеру (%s): %s", AI_BASE_URL, exc)
            raise

        message = response.choices[0].message
        if not message.tool_calls:
            return _parse_final_json(message.content)

        # content не должен быть None: часть провайдеров (например, Groq) отвечает 400 на null
        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ],
        })
        for tc in message.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(_run_tool(docs, args), ensure_ascii=False),
            })

    return _empty("Не удалось завершить подбор за отведённое число шагов — попробуйте переформулировать запрос.")


def keyword_search(query: str, db: Session) -> dict:
    """Запасной режим без нейросети: слова запроса плюс словарь связанных понятий."""
    tokens = tokenize(query)
    expansion = expand_query(tokens)
    ranked = rank(_published_docs(db), query, use_synonyms=True, limit=MAX_RESULTS)

    results = []
    for doc, _ in ranked:
        tags = matching_tags(doc, tokens, expansion)
        reason = ("Совпадение по темам: " + ", ".join(tags)) if tags else "Совпадение по названию и описанию"
        results.append({"card_id": doc.id, "reason": reason})

    if results:
        message = "Показан поиск по ключевым словам и связанным темам."
    else:
        message = "По этому запросу ничего не найдено. Попробуйте другие слова или откройте каталог."
    return {"message": message, "terms": (tokens + expansion)[:12], "results": results}
