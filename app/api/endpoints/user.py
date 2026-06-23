from fastapi import File, UploadFile, APIRouter, Depends, HTTPException
from app.database import get_async_db
from app.utils.auth import get_current_user, verify_password
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.crud import get_user_by_iin, update_user_password, get_user_by_phone
from app.models import User
from app.schemas import PhoneUpdate, User, UserOut, PasswordChangeRequest
from app.utils.uploads import safe_extension, read_within_limit, IMAGE_EXTS, MAX_IMAGE_BYTES
import os
import uuid

router = APIRouter()

@router.get("/by-iin/{iin}", response_model=UserOut)
async def read_user_by_iin(iin: str, db: AsyncSession = Depends(get_async_db)):
    user = await get_user_by_iin(db, iin)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

@router.post("/update-phone")
async def update_phone(
    phone_update: PhoneUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
):
    # Заново получаем пользователя из БД, привязанного к текущей сессии
    result = await db.execute(select(type(current_user)).where(type(current_user).id == current_user.id))
    user = result.scalar_one_or_none()

    existing = await get_user_by_phone(db, phone_update.phone)
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=400, detail="Этот номер уже используется")

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.phone = phone_update.phone
    await db.commit()
    await db.refresh(user)

    user_data = User.model_validate(user)
    return {
        "user": {
            "iin": user_data.iin,
            "role": user_data.role,
            "phone": user_data.phone,
            "photo": user_data.photo,
            "full_name": user_data.full_name,
            "short_name": user_data.short_name,
        }
    }

@router.post("/upload-photo")
async def upload_photo(
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
):
    # Повторно получаем пользователя в рамках текущей сессии
    result = await db.execute(select(type(current_user)).where(type(current_user).id == current_user.id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Создаём папку, если её нет
    folder = "static/photos"
    os.makedirs(folder, exist_ok=True)

    # Имя генерируем сами (не доверяем клиентскому), тип — только изображения.
    ext = safe_extension(photo.filename, IMAGE_EXTS)
    content = await read_within_limit(photo, MAX_IMAGE_BYTES)
    file_name = f"{user.id}_{uuid.uuid4().hex}{ext}"
    file_location = os.path.join(folder, file_name)

    try:
        with open(file_location, "wb") as f:
            f.write(content)
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка при сохранении файла")

    # Обновляем путь к фото
    user.photo = file_location
    await db.commit()
    await db.refresh(user)

    user_data = User.model_validate(user)
    return {
        "user": {
            "iin": user_data.iin,
            "role": user_data.role,
            "phone": user_data.phone,
            "photo": user_data.photo,
            "full_name": user_data.full_name,
            "short_name": user_data.short_name,
        }
    }

@router.patch("/change-password")
async def change_own_password(
    payload: PasswordChangeRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
):
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")
    await update_user_password(db, current_user, payload.new_password)
    return {"message": "Пароль успешно изменён"}