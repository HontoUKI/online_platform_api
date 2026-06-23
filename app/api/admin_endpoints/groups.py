from typing import List
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import crud, models
from app.database import get_async_db
from app.models import teacher_module_table, user_group_table
from app.models import Group as GroupModel, User as UserModel
from app.schemas import Group, GroupCreate, User, UserCreate
from app.utils.auth import get_current_admin_user
from app.utils.uploads import safe_extension, read_within_limit, EXCEL_EXTS, MAX_EXCEL_BYTES

router = APIRouter()


@router.post("/", response_model=Group)
async def create_group(
    group: GroupCreate,
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return await crud.create_group(db, group)


@router.get("/", response_model=List[Group])
async def get_all_groups(
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return await crud.get_all_groups(db)


@router.get("/{group_id}", response_model=Group)
async def get_group_by_id(
    group_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return await crud.get_group_by_id(db, group_id)


@router.post("/{group_id}/users", response_model=Group)
async def add_users_to_group(
    group_id: int,
    user_ids: List[int] = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return await crud.add_users_to_group(db, group_id, user_ids)


@router.get("/{group_id}/users", response_model=List[User])
async def get_group_users(
    group_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return await crud.get_group_users(db, group_id)


@router.delete("/{group_id}/users/{user_id}", response_model=Group)
async def remove_user_from_group(
    group_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return await crud.remove_user_from_group(db, group_id, user_id)


@router.post("/upload-excel")
async def upload_group_from_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_admin: UserModel = Depends(get_current_admin_user),
):
    safe_extension(file.filename, EXCEL_EXTS)
    content = await read_within_limit(file, MAX_EXCEL_BYTES)
    df = pd.read_excel(BytesIO(content))
    df.columns = [col.strip() for col in df.columns]

    expected_columns = {"Группа", "ИИН"}
    if "ФИО" not in df.columns:
        fio_parts = {"Фамилия", "Имя", "Отчество"}
        if fio_parts.issubset(df.columns):
            df["ФИО"] = (
                df["Фамилия"].astype(str).str.strip() + " " +
                df["Имя"].astype(str).str.strip()
            )

            if "Отчество" in df.columns:
                df["Отчество"] = df["Отчество"].fillna("").astype(str).str.strip()
                df["ФИО"] = df["ФИО"] + df["Отчество"].apply(lambda x: f" {x}" if x else "")

        else:
            raise HTTPException(status_code=400, detail="Ожидается либо столбец 'ФИО', либо тройка: 'Фамилия', 'Имя', 'Отчество'")

    if not expected_columns.issubset(df.columns):
        raise HTTPException(status_code=400, detail="Ожидаются столбцы: Группа, ИИН и ФИО (или Фамилия+Имя+Отчество)")


    group_name = str(df.iloc[0]["Группа"]).strip()
    group_desc = df.iloc[0].get("Описание", None)

    result = await db.execute(select(GroupModel).where(GroupModel.name == group_name))
    group = result.scalar_one_or_none()

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
    return {"message": f"{action} группа '{group.name}' с {len(created_user_ids)} пользователями."}


@router.delete("/{group_id}")
async def delete_group_only(
    group_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user),
):
    group = await crud.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    group.users.clear()
    await db.delete(group)
    await db.commit()

    return {"detail": f"Группа '{group.name}' удалена. Пользователи остались в системе."}


@router.delete("/{group_id}/with-users")
async def delete_group_with_users(
    group_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_admin: User = Depends(get_current_admin_user),
):
    stmt = (
        select(GroupModel)
        .options(selectinload(GroupModel.users))
        .where(GroupModel.id == group_id)
    )
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    # Оставляем админов — удаляем только студентов и преподавателей
    users_to_delete = [user for user in group.users if user.role != "admin"]
    user_ids = [user.id for user in users_to_delete]

    if user_ids:
        await db.execute(
            delete(teacher_module_table).where(
                teacher_module_table.c.teacher_id.in_(user_ids)
            )
        )
        await db.execute(
            delete(user_group_table).where(
                user_group_table.c.user_id.in_(user_ids)
            )
        )
        await db.execute(delete(UserModel).where(UserModel.id.in_(user_ids)))

    await db.delete(group)
    await db.commit()

    return {
        "detail": f"Группа '{group.name}' удалена. Удалено пользователей: {len(user_ids)}. Админы сохранены."
    }

