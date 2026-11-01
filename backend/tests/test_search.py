# -*- coding: utf-8 -*-
"""Запуск без зависимостей:  cd backend && python -m unittest discover -s tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.search import (  # noqa: E402
    SearchDoc, expand_query, html_to_text, matching_tags, rank, score, stem, tokenize,
)
from app.permissions import (  # noqa: E402
    FacultyAccessError, can_manage_faculty, can_view_card, resolve_card_faculty,
)
from app.taxonomy import MAX_TAGS_PER_CARD, normalize_tag, normalize_tags  # noqa: E402

CV = SearchDoc(1, "Система компьютерного зрения для распознавания объектов",
               "Нейросетевое распознавание объектов на видео в реальном времени",
               "Разработка кафедры технической кибернетики",
               ["компьютерное зрение", "нейронные сети", "распознавание образов"], "Факультет кибернетики")
ROBOT = SearchDoc(2, "Автономная мобильная платформа для склада",
                  "Робот-тележка с навигацией по лидару", "",
                  ["робототехника", "навигация", "лидар"], "Факультет кибернетики")
WATER = SearchDoc(3, "Биосенсор для анализа воды", "Экспресс-анализ качества воды", "",
                  ["биосенсоры", "экология"], "Факультет биотехнологий")
SOLAR = SearchDoc(4, "Управление солнечной электростанцией", "Умная система управления", "",
                  ["возобновляемая энергетика", "умные сети"], "Факультет энергетики")
DOCS = [CV, ROBOT, WATER, SOLAR]


class Tokenizing(unittest.TestCase):
    def test_tokenize_drops_stop_words_short_words_and_repeats(self):
        self.assertEqual(tokenize("Мне нужен робот для склада, робот!"), ["робот", "склада"])
        self.assertEqual(tokenize("ИИ и 3D-печать"), ["печать"])  # слова короче трёх букв отбрасываются
        self.assertEqual(tokenize(""), [])
        self.assertEqual(tokenize(None), [])

    def test_stem_handles_russian_endings(self):
        for word in ("робот", "роботов", "роботы", "робототехника"):
            self.assertEqual(stem(word), "робот", word)
        self.assertEqual(stem("зрение"), stem("зрения"))
        self.assertEqual(stem("компьютерное"), stem("компьютерного"))
        self.assertEqual(stem("Ёлка"), "елка")
        self.assertEqual(stem("лидар"), "лидар")  # короткие слова не обрезаются

    def test_html_to_text(self):
        self.assertEqual(html_to_text("<p>Привет, <b>мир</b>&nbsp;&amp; всем</p>").replace("\xa0", " "), "Привет, мир & всем")


class Ranking(unittest.TestCase):
    def test_direct_match_wins(self):
        ranked = rank(DOCS, "робот")
        self.assertEqual(ranked[0][0].id, 2)

    def test_related_topics_bridge_the_gap(self):
        # слова «робот» нет ни в тегах, ни в названии карточки по зрению,
        # но связанное понятие «компьютерное зрение» находит её
        ids = [d.id for d, _ in rank(DOCS, "нужен робот")]
        self.assertIn(1, ids)
        self.assertLess(ids.index(2), ids.index(1))  # прямое совпадение выше связанного

    def test_without_synonyms_no_bridge(self):
        ids = [d.id for d, _ in rank(DOCS, "робот", use_synonyms=False)]
        self.assertNotIn(1, ids)

    def test_unrelated_cards_are_not_returned(self):
        ids = [d.id for d, _ in rank(DOCS, "робот")]
        self.assertNotIn(3, ids)
        self.assertNotIn(4, ids)

    def test_morphology_in_queries(self):
        self.assertIn(1, [d.id for d, _ in rank(DOCS, "зрения нейронными сетями", use_synonyms=False)])
        self.assertIn(3, [d.id for d, _ in rank(DOCS, "анализировать воду")])

    def test_tags_outweigh_description(self):
        in_tags = SearchDoc(10, "Альфа", "", "", ["геном"], "")
        in_text = SearchDoc(11, "Бета", "", "геном человека изучают давно", [], "")
        ranked = rank([in_text, in_tags], "геном")
        self.assertEqual([d.id for d, _ in ranked], [10, 11])

    def test_all_query_words_matching_beats_partial(self):
        both = SearchDoc(20, "Умные сети для воды", "", "", ["вода", "сети"], "")
        one = SearchDoc(21, "Сети связи", "", "", ["сети"], "")
        self.assertEqual(rank([one, both], "вода сети", use_synonyms=False)[0][0].id, 20)

    def test_empty_and_stop_word_queries(self):
        self.assertEqual(rank(DOCS, ""), [])
        self.assertEqual(rank(DOCS, "для что как"), [])

    def test_limit_and_stable_order(self):
        twins = [SearchDoc(i, "Робот", "", "", [], "") for i in (7, 5, 6)]
        self.assertEqual([d.id for d, _ in rank(twins, "робот")], [5, 6, 7])
        self.assertEqual(len(rank(twins, "робот", limit=2)), 2)

    def test_score_zero_when_nothing_matches(self):
        self.assertEqual(score(WATER, tokenize("робот")), 0)

    def test_expand_query_skips_words_already_in_query(self):
        extra = expand_query(tokenize("робот зрение"))
        self.assertNotIn("зрение", extra)
        self.assertIn("навигация", extra)
        self.assertEqual(expand_query(tokenize("абракадабра")), [])


class Explanation(unittest.TestCase):
    def test_matching_tags_for_direct_and_related_topics(self):
        tokens = tokenize("нужен робот")
        self.assertEqual(matching_tags(ROBOT, tokens), ["робототехника"])
        self.assertEqual(matching_tags(CV, tokens), [])  # напрямую ничего нет
        self.assertEqual(matching_tags(CV, tokens, expand_query(tokens)), ["компьютерное зрение"])


class Permissions(unittest.TestCase):
    def test_manage(self):
        self.assertTrue(can_manage_faculty("superuser", None, 5))
        self.assertTrue(can_manage_faculty("admin", 2, 2))
        self.assertFalse(can_manage_faculty("admin", 2, 3))
        self.assertFalse(can_manage_faculty("admin", None, None))  # админ без факультета — ничего не может
        self.assertFalse(can_manage_faculty("user", 2, 2))

    def test_view(self):
        self.assertTrue(can_view_card("published", None, None, 1))
        self.assertFalse(can_view_card("draft", "user", None, 1))
        self.assertFalse(can_view_card("draft", "admin", 2, 1))
        self.assertTrue(can_view_card("draft", "admin", 1, 1))
        self.assertTrue(can_view_card("draft", "superuser", None, 1))

    def test_resolve_faculty(self):
        self.assertEqual(resolve_card_faculty("superuser", None, 4), 4)
        self.assertIsNone(resolve_card_faculty("superuser", None, None))
        self.assertEqual(resolve_card_faculty("admin", 2, None), 2)
        self.assertEqual(resolve_card_faculty("admin", 2, 2), 2)
        with self.assertRaises(FacultyAccessError):
            resolve_card_faculty("admin", 2, 3)  # подмена факультета в запросе — отказ
        with self.assertRaises(FacultyAccessError):
            resolve_card_faculty("admin", None, 2)
        with self.assertRaises(FacultyAccessError):
            resolve_card_faculty("user", None, 2)


class Tags(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_tag("  Компьютерное   Зрение "), "компьютерное зрение")
        self.assertEqual(normalize_tag("ЁЖ"), "еж")
        self.assertEqual(normalize_tag("   "), "")
        self.assertEqual(normalize_tag("3D-печать"), "3d-печать")
        self.assertEqual(normalize_tag("C++"), "c++")

    def test_reject_bad_tags(self):
        for bad in ("<script>", "a" * 41, "тег;drop", 'a"b'):
            with self.assertRaises(ValueError, msg=bad):
                normalize_tag(bad)

    def test_list_dedupes_and_limits(self):
        self.assertEqual(normalize_tags(["ИИ", "ии", " ", "Робот"]), ["ии", "робот"])
        self.assertEqual(normalize_tags(None), [])
        with self.assertRaises(ValueError):
            normalize_tags([f"тег{i}" for i in range(MAX_TAGS_PER_CARD + 1)])


if __name__ == "__main__":
    unittest.main()
