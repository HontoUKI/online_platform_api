from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud, schemas
from app.database import get_async_db
from app.utils.auth import verify_password, create_access_token, get_current_user
from app.models import User
from fastapi import Request
from datetime import datetime, timedelta, timezone

from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()


# Простое in-memory хранилище (в проде — Redis!)
attempts_cache = {}

MAX_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 5

@router.post("/login")
async def login(request: schemas.LoginRequest, db: AsyncSession = Depends(get_async_db)):
    iin = request.iin
    now = datetime.now(timezone.utc)

    # Проверяем наличие блокировки
    login_attempt = attempts_cache.get(iin)
    if login_attempt:
        if login_attempt["count"] >= MAX_ATTEMPTS:
            if now < login_attempt["unlock_at"]:
                remaining = int((login_attempt["unlock_at"] - now).total_seconds() / 60)
                raise HTTPException(status_code=403, detail=f"Превышено число попыток.Повторите через {remaining} мин.")
            else:
                # Блокировка истекла — сбрасываем
                attempts_cache.pop(iin)

    user = await crud.get_user_by_iin(db, request.iin)
    if not user:
        _track_failed_attempt(iin)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неправильный ИИН или пароль")

    await db.refresh(user)

    if not verify_password(request.password, user.hashed_password):
        _track_failed_attempt(iin)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неправильный ИИН или пароль")

    # Успешный вход — очищаем попытки
    if iin in attempts_cache:
        attempts_cache.pop(iin)

    access_token = create_access_token(data={"sub": user.iin})
    user_data = schemas.User.model_validate(user)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "iin": user_data.iin,
            "role": user_data.role,
            "phone": user_data.phone,
            "photo": user_data.photo,
            "full_name": user_data.full_name,
            "short_name": user_data.short_name,
        }
    }

@router.get("/check")
async def check_auth(current_user: User = Depends(get_current_user)):
    return {"status": "ok", "user": {"iin": current_user.iin, "role": current_user.role}}

# Локальная фиксация неуспешной попытки
def _track_failed_attempt(iin: str):
    now = datetime.now(timezone.utc)
    attempt = attempts_cache.get(iin)

    if not attempt:
        attempts_cache[iin] = {
            "count": 1,
            "unlock_at": now + timedelta(minutes=LOCK_DURATION_MINUTES)
        }
    else:
        attempt["count"] += 1
        # обновляем только если достижение лимита
        if attempt["count"] >= MAX_ATTEMPTS:
            attempt["unlock_at"] = now + timedelta(minutes=LOCK_DURATION_MINUTES)

@router.post("/token")
async def login_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db),
):
    user = await crud.get_user_by_iin(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный ИИН или пароль")

    access_token = create_access_token(data={"sub": user.iin})
    return {"access_token": access_token, "token_type": "bearer"}
