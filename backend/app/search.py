# -*- coding: utf-8 -*-
"""Поиск по карточкам без нейросети: слова, основы, веса полей и словарь связанных понятий.

Нужен в двух местах:
  * обычный поиск в каталоге (GET /cards?q=…);
  * запасной режим ИИ-поиска, когда ключ нейросети не задан или провайдер недоступен.

Русская морфология решается грубо, но достаточно для каталога: слова от шести букв
сводятся к первым пяти (робот, роботов, робототехника -> «робот»). Слова короче шести
букв остаются как есть. Словарь связанных понятий (SYNONYM_CLUSTERS) подмешивает к
запросу родственные темы: «робот» находит и разработки по компьютерному зрению.
Нейросеть делает то же самое гибче, но этот слой работает без внешних сервисов.
Только стандартная библиотека.
"""
import html
import re
from dataclasses import dataclass, field

_WORD = re.compile(r"[\w+#]+", re.UNICODE)
STEM_LENGTH = 5

STOP_WORDS = {
    "для", "что", "как", "это", "или", "при", "над", "под", "про", "без", "все", "его",
    "она", "они", "мне", "нам", "нужен", "нужна", "нужно", "нужны", "хочу", "ищу", "ищем",
    "найти", "есть", "можно", "чтобы", "который", "которая", "которые", "между", "также",
    "очень", "свой", "своя", "свои", "наш", "наша", "наши", "the", "and", "for", "with",
}

# Вес совпадения по полям карточки: теги и название важнее длинного описания
FIELD_WEIGHTS = {"tags": 3.0, "title": 2.5, "summary": 1.5, "faculty": 1.0, "text": 1.0}
# Совпадения по подмешанным (связанным) понятиям весят вдвое меньше прямых
# и считаются только по тегам, названию и краткому описанию
EXPANSION_FIELDS = ("tags", "title", "summary")
EXPANSION_FACTOR = 0.5


def stem(word: str) -> str:
    word = word.lower().replace("ё", "е")
    return word[:STEM_LENGTH] if len(word) > STEM_LENGTH else word


def tokenize(text: str) -> list:
    """Слова запроса: без служебных и слишком коротких, без повторов, порядок сохраняется."""
    seen, tokens = set(), []
    for word in _WORD.findall((text or "").lower().replace("ё", "е")):
        if len(word) >= 3 and word not in STOP_WORDS and word not in seen:
            seen.add(word)
            tokens.append(word)
    return tokens


def stems(text: str) -> set:
    return {stem(w) for w in tokenize(text)}


def html_to_text(value: str) -> str:
    plain = html.unescape(re.sub(r"<[^>]*>", " ", value or ""))
    return re.sub(r"\s+", " ", plain).strip()


# (слова-триггеры, связанные понятия). Список можно свободно править и дополнять.
SYNONYM_CLUSTERS = [
    ({"робот", "манипулятор", "дрон", "беспилотник", "автоматизация", "мехатроника"},
     ["компьютерное зрение", "навигация", "сенсоры", "автоматизация"]),
    ({"медицина", "врач", "диагностика", "здоровье", "пациент", "больница"},
     ["биосенсоры", "нейронные сети", "анализ изображений", "биотехнологии"]),
    ({"энергия", "электричество", "солнечный", "аккумулятор", "батарея"},
     ["возобновляемая энергетика", "накопитель энергии", "умные сети", "электроника"]),
    ({"интеллект", "искусственный", "нейросеть", "нейронный", "обучение"},
     ["машинное обучение", "нейронные сети", "анализ данных"]),
    ({"экология", "вода", "загрязнение", "очистка", "природа"},
     ["биосенсоры", "мониторинг", "анализ воды", "экология"]),
    ({"материал", "легкий", "прочный", "конструкция", "деталь"},
     ["композиты", "аддитивные технологии", "производство"]),
    ({"еда", "питание", "продукт", "пищевой", "белок"},
     ["биотехнологии", "пищевая промышленность", "белок"]),
]
_CLUSTERS = [({stem(t) for t in triggers}, expansion) for triggers, expansion in SYNONYM_CLUSTERS]


def expand_query(tokens) -> list:
    """Связанные понятия для слов запроса (в виде слов; дубликатов нет)."""
    present = {stem(t) for t in tokens}
    extra = []
    for triggers, expansion in _CLUSTERS:
        if present & triggers:
            for phrase in expansion:
                for word in tokenize(phrase):
                    if word not in extra and stem(word) not in present:
                        extra.append(word)
    return extra


@dataclass
class SearchDoc:
    """Карточка в виде, удобном для поиска."""
    id: int
    title: str = ""
    summary: str = ""
    text: str = ""
    tags: list = field(default_factory=list)
    faculty: str = ""


def _field_stems(doc: SearchDoc) -> dict:
    return {
        "tags": stems(" ".join(doc.tags)),
        "title": stems(doc.title),
        "summary": stems(doc.summary),
        "faculty": stems(doc.faculty),
        "text": stems(doc.text),
    }


def score(doc: SearchDoc, tokens, expansion=()) -> float:
    """Оценка карточки; 0 — ничего общего с запросом."""
    fields = _field_stems(doc)
    query_stems = [stem(t) for t in tokens]
    total, matched = 0.0, 0

    for q in query_stems:
        weight = sum(w for name, w in FIELD_WEIGHTS.items() if q in fields[name])
        if weight:
            matched += 1
            total += weight

    for word in expansion:
        q = stem(word)
        total += EXPANSION_FACTOR * sum(FIELD_WEIGHTS[name] for name in EXPANSION_FIELDS if q in fields[name])

    if matched and query_stems:
        total += 2.0 * matched / len(query_stems)  # бонус за то, что совпали все слова запроса
    return round(total, 3)


def rank(docs, query: str, use_synonyms: bool = True, limit=None) -> list:
    """[(карточка, оценка)] по убыванию оценки; без совпадений в выдачу не попадают."""
    tokens = tokenize(query)
    if not tokens:
        return []
    expansion = expand_query(tokens) if use_synonyms else []
    scored = [(doc, score(doc, tokens, expansion)) for doc in docs]
    scored = [(doc, s) for doc, s in scored if s > 0]
    scored.sort(key=lambda pair: (-pair[1], pair[0].id))
    return scored[:limit] if limit else scored


def matching_tags(doc: SearchDoc, tokens, expansion=()) -> list:
    """Теги карточки, из-за которых она нашлась (для пояснения «почему подходит»)."""
    wanted = {stem(t) for t in tokens} | {stem(w) for w in expansion}
    return [tag for tag in doc.tags if stems(tag) & wanted]
