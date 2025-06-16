from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_db
from app.utils.auth import get_current_admin_user
from typing import List
import app.crud as crud
from app.schemas import GroupCreate, Group, User
from fastapi import UploadFile, File
from io import BytesIO
import pandas as pd
from sqlalchemy.exc import IntegrityError
from app.models import User as UserModel
from app.schemas import UserCreate

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

    expected_columns = {"Группа", "ФИО", "ИИН"}
    if not expected_columns.issubset(df.columns):
        raise HTTPException(status_code=400, detail="Ожидаются столбцы: Группа, ФИО, ИИН")

    group_name = str(df.iloc[0]["Группа"]).strip()
    group_desc = df.iloc[0].get("Описание", None)

    group = await crud.create_group(db, GroupCreate(name=group_name, description=group_desc))

    created_user_ids = []
    for row in df.itertuples():
        try:
            iin = str(row.ИИН).strip()
            full_name = str(row.ФИО).strip()
            password = iin[:3] + iin[-3:]

            user_create = UserCreate(
                iin=iin,
                full_name=full_name,
                password=password
            )

            user = await crud.create_user(db, user_create)
        except IntegrityError:
            await db.rollback()
            user = await crud.get_user_by_iin(db, iin)
            if not user:
                continue  # пропускаем неудачные строки

        created_user_ids.append(user.id)

    await crud.add_users_to_group(db, group.id, created_user_ids)

    return {"message": f"Создана группа '{group.name}' с {len(created_user_ids)} пользователями."}
