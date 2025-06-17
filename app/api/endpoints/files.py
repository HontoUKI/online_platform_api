from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    full_path = os.path.join("static", file_path)

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="Файл не найден")

    filename = os.path.basename(full_path)

    return FileResponse(
        full_path,
        filename=filename,
        media_type="application/octet-stream"
    )
