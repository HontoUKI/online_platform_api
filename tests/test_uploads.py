"""Тесты валидации загрузок: тип, размер и санитизация имени."""
import asyncio
import io

import pytest
from fastapi import HTTPException, UploadFile

from app.utils import uploads


def make_upload(filename: str, size: int = 10) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(b"x" * size))


def test_image_extension_accepts_allowed():
    assert uploads.safe_extension("avatar.PNG", uploads.IMAGE_EXTS) == ".png"


def test_image_extension_rejects_svg():
    # SVG может нести скрипт → XSS, поэтому запрещён для аватаров.
    with pytest.raises(HTTPException) as exc:
        uploads.safe_extension("evil.svg", uploads.IMAGE_EXTS)
    assert exc.value.status_code == 400


def test_extension_rejects_null_byte():
    with pytest.raises(HTTPException):
        uploads.safe_extension("weird.\x00php", None)


def test_traversal_filename_yields_no_usable_extension():
    # Имя с путём не даёт «опасного» расширения, а само имя в путь не попадает
    # (сервер генерирует имя сам). Здесь — что extension безопасен/пуст.
    assert uploads.safe_extension("../../etc/passwd", None) == ""
    assert uploads.safe_extension("a/b/c.png", uploads.IMAGE_EXTS) == ".png"


def test_read_within_limit_rejects_oversize():
    big = make_upload("a.png", size=uploads.MAX_IMAGE_BYTES + 1)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(uploads.read_within_limit(big, uploads.MAX_IMAGE_BYTES))
    assert exc.value.status_code == 413


def test_read_within_limit_allows_normal():
    small = make_upload("a.png", size=100)
    content = asyncio.run(uploads.read_within_limit(small, uploads.MAX_IMAGE_BYTES))
    assert content == b"x" * 100


def test_random_filename_uses_extension():
    name = uploads.random_filename(".pdf")
    assert name.endswith(".pdf")
    assert "/" not in name and "\\" not in name
