# -*- coding: utf-8 -*-
"""Проверки загружаемых файлов: тип по содержимому, расширения, имена. Только stdlib."""
import re
from urllib.parse import quote

IMAGE_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}

# Что можно выкладывать как файл релиза. Скрипты и разметка (.sh, .bat, .html, .svg …)
# намеренно не входят: файлы отдаются только как скачивание, но лишнего не нужно.
# Составные расширения идут первыми — проверка идёт по порядку.
ALLOWED_FILE_EXTS = (
    ".tar.gz", ".tar.xz", ".tar.bz2",
    ".zip", ".7z", ".tgz", ".gz", ".xz", ".bz2", ".tar",
    ".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".appimage",
    ".apk", ".ipa", ".jar", ".whl",
)


def sniff_image(head: bytes):
    """MIME изображения по первым байтам (расширению и заголовкам клиента не верим)."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def safe_display_name(filename, max_len: int = 120) -> str:
    """Имя для показа и скачивания: без пути, управляющих и опасных символов."""
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(ch for ch in name if ch.isprintable() and ch not in '<>:"|?*')
    name = re.sub(r"\s+", " ", name).strip(" .")
    if len(name) > max_len:
        stem, dot, ext = name.rpartition(".")
        if dot and 0 < len(ext) <= 15:
            name = stem[: max_len - len(ext) - 1] + "." + ext
        else:
            name = name[:max_len]
    return name or "file"


def allowed_file_ext(filename):
    """Расширение из белого списка (в нижнем регистре) или None."""
    name = safe_display_name(filename).lower()
    for ext in ALLOWED_FILE_EXTS:
        if name.endswith(ext) and len(name) > len(ext):
            return ext
    return None


def content_disposition(filename, disposition: str = "attachment") -> str:
    """Заголовок Content-Disposition с ASCII-запасным именем и UTF-8 (RFC 5987)."""
    name = safe_display_name(filename)
    ascii_name = re.sub(r"[^A-Za-z0-9._ -]", "_", name) or "file"
    return f'{disposition}; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(name, safe="")}'
