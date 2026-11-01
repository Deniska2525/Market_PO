# -*- coding: utf-8 -*-
"""Запуск без зависимостей:  cd backend && python -m unittest discover -s tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.uploads import (  # noqa: E402
    allowed_file_ext, content_disposition, safe_display_name, sniff_image,
)


class UploadChecks(unittest.TestCase):
    def test_sniff_image(self):
        self.assertEqual(sniff_image(b"\x89PNG\r\n\x1a\n" + b"0" * 8), "image/png")
        self.assertEqual(sniff_image(b"\xff\xd8\xff\xe0" + b"0" * 12), "image/jpeg")
        self.assertEqual(sniff_image(b"GIF89a" + b"0" * 10), "image/gif")
        self.assertEqual(sniff_image(b"RIFF\x00\x00\x00\x00WEBPVP8 "), "image/webp")
        for fake in (b"<svg xmlns=", b"<html><script>", b"MZ\x90\x00", b"", b"RIFF\x00\x00\x00\x00WAVEfmt "):
            self.assertIsNone(sniff_image(fake), fake)

    def test_allowed_ext(self):
        self.assertEqual(allowed_file_ext("App-1.0.TAR.GZ"), ".tar.gz")
        self.assertEqual(allowed_file_ext("setup.exe"), ".exe")
        self.assertEqual(allowed_file_ext("Tool.AppImage"), ".appimage")
        for bad in ("run.sh", "page.html", "x.svg", "noext", ".zip", "a.exe.txt", "a.php", ""):
            self.assertIsNone(allowed_file_ext(bad), bad)

    def test_safe_display_name(self):
        self.assertEqual(safe_display_name("../../etc/passwd"), "passwd")
        self.assertEqual(safe_display_name("C:\\Users\\me\\a.zip"), "a.zip")
        self.assertEqual(safe_display_name("a\x00b\n.zip"), "ab.zip")
        self.assertEqual(safe_display_name('we<ird>:"name|?.zip'), "weirdname.zip")
        self.assertEqual(safe_display_name(""), "file")
        long = safe_display_name("x" * 300 + ".zip")
        self.assertLessEqual(len(long), 120)
        self.assertTrue(long.endswith(".zip"))

    def test_content_disposition(self):
        h = content_disposition("Приложение 1.0.zip")
        self.assertTrue(h.startswith('attachment; filename="'))
        self.assertIn("filename*=UTF-8''%D0%9F", h)
        self.assertNotIn("\n", h)
        self.assertEqual(h.count('"'), 2)
        self.assertNotIn('"', content_disposition('a"b.zip').split("filename*")[0][len('attachment; filename="'):-3])


if __name__ == "__main__":
    unittest.main()
