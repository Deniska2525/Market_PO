# -*- coding: utf-8 -*-
"""Запуск без зависимостей:  cd backend && python -m unittest discover -s tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.sanitize import sanitize_html, safe_url  # noqa: E402


class SanitizeTests(unittest.TestCase):
    def test_keeps_safe_markup(self):
        self.assertEqual(sanitize_html("<p>Hi <strong>you</strong></p>"), "<p>Hi <strong>you</strong></p>")
        self.assertEqual(
            sanitize_html('<a href="https://e.com/?a=1&b=2">x</a>'),
            '<a href="https://e.com/?a=1&amp;b=2" rel="noopener noreferrer">x</a>')

    def test_xss_battery(self):
        cases = [
            "<script>alert(1)</script><p>hi</p>",
            '<a href="javascript:alert(1)">x</a>',
            '<a href=" jAvA\tscript:alert(1)">x</a>',
            '<a href="&#106;avascript:alert(1)">x</a>',
            "<img src=x onerror=alert(1)>",
            '<img src="javascript:alert(1)">',
            '<p onclick="alert(1)">t</p>',
            "<svg><script>alert(1)</script></svg>x",
            "<style>body{}</style>ok",
            "<iframe src=//evil></iframe>",
            "<script><script>a</script>b</script>c",
            '<a href="data:text/html;base64,AAAA">x</a>',
            "<p>unclosed <b>bold",
            '"><script>alert(1)</script>',
            "<scr<script>ipt>alert(1)</script>",
        ]
        for c in cases:
            out = sanitize_html(c).lower()
            for needle in ("<script", "javascript:", "onerror", "onclick", "<iframe", "<svg", "<style", "data:"):
                self.assertNotIn(needle, out, f"{c!r} -> {out!r}")

    def test_specific_outputs(self):
        self.assertEqual(sanitize_html("<script>x</script><p>hi</p>"), "<p>hi</p>")
        self.assertEqual(sanitize_html("<a href=\"javascript:x\">t</a>"), "<a>t</a>")
        self.assertEqual(sanitize_html("<img src=x onerror=y>"), "")
        self.assertEqual(sanitize_html('<img src="/static/a.png" onerror="y">'), '<img src="/static/a.png" alt="">')
        self.assertEqual(sanitize_html("<p>a<b>b"), "<p>a<b>b</b></p>")
        self.assertEqual(sanitize_html("a < b & c"), "a &lt; b &amp; c")

    def test_safe_url(self):
        self.assertIsNone(safe_url("java\tscript:alert(1)"))
        self.assertIsNone(safe_url("//evil.com"))
        self.assertEqual(safe_url("mailto:a@b.c"), "mailto:a@b.c")
        self.assertIsNone(safe_url("mailto:a@b.c", allow_mailto=False))


if __name__ == "__main__":
    unittest.main()
