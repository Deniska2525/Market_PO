# -*- coding: utf-8 -*-
"""Очистка HTML по белому списку тегов и проверка ссылок. Только стандартная библиотека.

Описание карточки хранится как HTML из визуального редактора. Ему нельзя верить:
sanitize_html() пересобирает разметку заново, пропуская только разрешённые теги
и безопасные ссылки, а весь текст и атрибуты экранирует.
"""
import html
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

def safe_url(value, allow_mailto: bool = True):
    """Возвращает нормализованный безопасный URL или None.

    Допустимо: http(s)://..., относительные /path (но не //host) и mailto:.
    Управляющие символы и пробелы внутри схемы вырезаются, поэтому
    «java\\tscript:...» не пройдёт.
    """
    v = re.sub(r"[\x00-\x20\x7f-\x9f]+", "", value or "")
    if not v:
        return None
    if v.startswith("/") and not v.startswith("//") and "\\" not in v:
        return v
    parsed = urlparse(v)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return v
    if allow_mailto and parsed.scheme == "mailto" and parsed.path:
        return v
    return None


_ALLOWED_TAGS = {
    "p", "br", "hr", "strong", "b", "em", "i", "u", "s", "ul", "ol", "li",
    "h2", "h3", "h4", "blockquote", "code", "pre", "a", "img",
}
_VOID_TAGS = {"br", "hr", "img"}
# Эти теги выбрасываются вместе с содержимым
_DROP_WITH_CONTENT = {
    "script", "style", "iframe", "object", "embed", "noscript",
    "template", "svg", "math", "title", "textarea",
}
_MAX_DEPTH = 50


class _Sanitizer(HTMLParser):
    """Пересобирает HTML по белому списку: на выход попадает только то,
    что мы сами сгенерировали, а весь текст и атрибуты экранируются."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.stack = []
        self.skip_tag = None
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_depth += 1
            return
        if tag in _DROP_WITH_CONTENT:
            self.skip_tag, self.skip_depth = tag, 1
            return
        if tag not in _ALLOWED_TAGS:
            return

        attrs = dict(attrs)
        if tag == "img":
            src = safe_url(attrs.get("src"), allow_mailto=False)
            if not src:
                return
            alt = html.escape(attrs.get("alt") or "", quote=True)
            self.out.append(f'<img src="{html.escape(src, quote=True)}" alt="{alt}">')
            return
        if tag in _VOID_TAGS:
            self.out.append(f"<{tag}>")
            return
        if len(self.stack) >= _MAX_DEPTH:
            return

        if tag == "a":
            href = safe_url(attrs.get("href"))
            if href:
                self.out.append(f'<a href="{html.escape(href, quote=True)}" rel="noopener noreferrer">')
            else:
                self.out.append("<a>")
        else:
            self.out.append(f"<{tag}>")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_depth -= 1
                if self.skip_depth == 0:
                    self.skip_tag = None
            return
        if tag in _VOID_TAGS or tag not in _ALLOWED_TAGS or tag not in self.stack:
            return
        while self.stack:
            top = self.stack.pop()
            self.out.append(f"</{top}>")
            if top == tag:
                break

    def handle_data(self, data):
        if not self.skip_tag:
            self.out.append(html.escape(data, quote=False))

    def result(self) -> str:
        while self.stack:
            self.out.append(f"</{self.stack.pop()}>")
        return "".join(self.out)


def sanitize_html(value: str) -> str:
    parser = _Sanitizer()
    parser.feed(value)
    parser.close()
    return parser.result()
