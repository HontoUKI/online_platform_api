import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.utils.auth import get_current_user
from app.models import User

router = APIRouter()

# Корень раздаваемых файлов. Любой путь обязан резолвиться строго внутри него.
STATIC_ROOT = os.path.realpath("static")


def resolve_static_path(file_path: str) -> str:
    """Безопасно резолвит путь внутри ``static/``.

    Блокирует выход за пределы каталога (path traversal через ``..``), иначе
    эндпоинт позволял бы скачать любой файл сервера, включая ``.env`` и исходники.
    """
    full_path = os.path.realpath(os.path.join(STATIC_ROOT, file_path))
    if full_path != STATIC_ROOT and not full_path.startswith(STATIC_ROOT + os.sep):
        raise HTTPException(status_code=403, detail="Недопустимый путь к файлу")
    return full_path


@router.get("/download/{file_path:path}")
async def download_file(
    file_path: str,
    current_user: User = Depends(get_current_user),
):
    full_path = resolve_static_path(file_path)

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(
        full_path,
        filename=os.path.basename(full_path),
        media_type="application/octet-stream",
    )
