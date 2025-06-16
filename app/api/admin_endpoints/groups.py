from typing import List
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models
from app.database import get_async_db
from app.models import User as UserModel
from app.schemas import Group, GroupCreate, User, UserCreate
from app.utils.auth import get_current_admin_user


router = APIRouter()

@router.post("/", response_model=Group)
async def create_group(
    group: GroupCreate,
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user)
):
    return await crud.create_group(db, group)

@router.get("/", response_model=List[Group])
async def get_all_groups(
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user)
):
    return await crud.get_all_groups(db)

@router.get("/{group_id}", response_model=Group)
async def get_group_by_id(
    group_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user)
):
    return await crud.get_group_by_id(db, group_id)

@router.post("/{group_id}/users", response_model=Group)
async def add_users_to_group(
    group_id: int,
    user_ids: List[int] = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user)
):
    return await crud.add_users_to_group(db, group_id, user_ids)

@router.get("/{group_id}/users", response_model=List[User])
async def get_group_users(
    group_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user)
):
    return await crud.get_group_users(db, group_id)

@router.delete("/{group_id}/users/{user_id}", response_model=Group)
async def remove_user_from_group(
    group_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user)
):
    return await crud.remove_user_from_group(db, group_id, user_id)

@router.post("/upload-excel")
async def upload_group_from_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_admin: UserModel = Depends(get_current_admin_user)
):
    content = await file.read()
    df = pd.read_excel(BytesIO(content))
    df.columns = [col.strip() for col in df.columns]

    expected_columns = {"Группа", "ФИО", "ИИН"}
    if not expected_columns.issubset(df.columns):
        raise HTTPException(status_code=400, detail="Ожидаются столбцы: Группа, ФИО, ИИН")

    group_name = str(df.iloc[0]["Группа"]).strip()
    group_desc = df.iloc[0].get("Описание", None)

    # Найти или создать группу
    existing = await db.execute(
        select(models.Group).where(models.Group.name == group_name)
    )
    group = existing.scalar_one_or_none()

    if not group:
        group = await crud.create_group(db, GroupCreate(name=group_name, description=group_desc))
        group_created = True
    else:
        group_created = False

    created_user_ids = []
    for row in df.itertuples():
        iin = str(row.ИИН).strip()
        full_name = str(row.ФИО).strip()
        password = iin[:3] + iin[-3:]

        user = await crud.get_user_by_iin(db, iin)
        if user:
            created_user_ids.append(user.id)
            continue

        try:
            user_create = UserCreate(iin=iin, full_name=full_name, password=password)
            user = await crud.create_user(db, user_create)
            created_user_ids.append(user.id)
        except IntegrityError:
            await db.rollback()
            existing_user = await crud.get_user_by_iin(db, iin)
            if existing_user:
                created_user_ids.append(existing_user.id)

    await crud.add_users_to_group(db, group.id, created_user_ids)

    action = "Создана" if group_created else "Обновлена"
    return {
        "message": f"{action} группа '{group.name}' с {len(created_user_ids)} пользователями."
    }

