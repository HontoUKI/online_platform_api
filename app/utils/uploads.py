"""Валидация и безопасное сохранение загружаемых файлов.

Две задачи:
1. Имя файла генерируется на сервере (uuid) — клиентское имя НЕ используется в пути,
   иначе ``f"{id}_{filename}"`` с ``../`` позволял бы записать файл вне каталога.
2. Ограничение размера и (где уместно) типа файла.
"""
import os
import uuid

from fastapi import HTTPException, UploadFile

# Картинки для аватаров. SVG намеренно НЕ разрешён (может содержать скрипт → XSS,
# т.к. аватары отдаются инлайн из /static/photos).
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Материалы уроков.
DOC_EXTS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".csv", ".txt",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm", ".mov", ".mp3", ".zip",
}

EXCEL_EXTS = {".xls", ".xlsx"}

MAX_IMAGE_BYTES = 5 * 1024 * 1024       # 5 МБ
MAX_DOC_BYTES = 50 * 1024 * 1024        # 50 МБ
MAX_HOMEWORK_BYTES = 20 * 1024 * 1024   # 20 МБ суммарно на одну работу
MAX_HOMEWORK_FILES = 5                  # до 5 файлов на одну работу
MAX_EXCEL_BYTES = 10 * 1024 * 1024      # 10 МБ


def safe_extension(filename: str | None, allowed: set[str] | None) -> str:
    """Возвращает безопасное расширение в нижнем регистре.

    ``allowed=None`` — любой тип разрешён (но имя всё равно санитизируется).
    """
    ext = os.path.splitext(filename or "")[1].lower()
    if any(c in ext for c in ("/", "\\", "\x00")):
        raise HTTPException(status_code=400, detail="Недопустимое имя файла")
    if allowed is not None and ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый тип файла: {ext or 'без расширения'}",
        )
    return ext


async def read_within_limit(file: UploadFile, max_bytes: int) -> bytes:
    """Читает файл целиком, отклоняя превышение лимита (413)."""
    content = await file.read()
    if len(content) > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"Файл слишком большой (до {limit_mb} МБ)")
    return content


def random_filename(ext: str) -> str:
    """Случайное безопасное имя файла."""
    return f"{uuid.uuid4().hex}{ext}"
