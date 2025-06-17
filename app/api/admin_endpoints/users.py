from typing import List

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException, status

from app.crud import create_user, get_user_by_iin, update_user_password
from app.database import get_async_db
from app.models import (
    LessonSubmission,
    Result,
    Subject,
    User as UserModel,
    user_group_table,
    teacher_module_table,
)
from app.schemas import PasswordResetRequest, User as UserSchema, UserCreate
from app.utils.auth import get_current_admin_user

router = APIRouter(tags=["admin_users"])


@router.post("/", response_model=UserSchema)
async def admin_create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_async_db),
    current_admin=Depends(get_current_admin_user),
):
    existing_iin = await db.execute(
        select(UserModel).where(UserModel.iin == user_data.iin)
    )
    if existing_iin.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Пользователь с таким ИИН уже существует")

    existing_phone = await db.execute(
        select(UserModel).where(UserModel.phone == user_data.phone)
    )
    if existing_phone.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Номер телефона уже используется")

    user = await create_user(db, user_data)
    return user


@router.get("/", response_model=List[UserSchema])
async def get_all_users(
    db: AsyncSession = Depends(get_async_db),
    current_admin=Depends(get_current_admin_user),
):
    result = await db.execute(select(UserModel))
    return result.scalars().all()


@router.delete("/{iin}")
async def delete_user(
    iin: str,
    db: AsyncSession = Depends(get_async_db),
    current_admin=Depends(get_current_admin_user),
):
    user = await get_user_by_iin(db, iin)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Нельзя удалить администратора")

    await db.execute(delete(Result).where(Result.user_id == user.id))
    await db.execute(delete(LessonSubmission).where(LessonSubmission.user_id == user.id))

    await db.execute(
        Subject.__table__.update()
        .where(Subject.teacher_id == user.id)
        .values(teacher_id=None)
    )

    user.groups.clear()
    user.teaching_modules.clear()

    await db.delete(user)
    await db.commit()

    return {"detail": f"Пользователь {iin} и связанные связи удалены"}


@router.patch("/reset_password")
async def admin_change_user_password(
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(get_async_db),
    current_admin=Depends(get_current_admin_user),
):
    user = await get_user_by_iin(db, payload.user_iin)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    await update_user_password(db, user, payload.new_password)
