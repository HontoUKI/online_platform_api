from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.database import get_async_db
from app.utils.auth import (
    get_current_admin_user,
    get_current_teacher_user,
    get_current_user,
)

router = APIRouter()


# Модули (только админ)

@router.post("/", response_model=schemas.ModuleCreate)
async def create_module(
    module_in: schemas.ModuleCreate,
    db: AsyncSession = Depends(get_async_db),
    current_admin: models.User = Depends(get_current_admin_user)
):
    return await crud.create_module(db, module_in)

@router.get("/", response_model=List[schemas.Module])
async def list_modules(
    db: AsyncSession = Depends(get_async_db),
    current_admin: models.User = Depends(get_current_admin_user)
):
    modules = await crud.get_modules(db)
    return modules

@router.get("/with-teachers", response_model=List[schemas.ModuleWithTeachers])
async def get_modules_full(
    db: AsyncSession = Depends(get_async_db),
    current_admin: models.User = Depends(get_current_admin_user)
):
    return await crud.get_modules_with_teachers(db)

@router.put("/{module_id}", response_model=schemas.ModuleUpdate)
async def update_module(
    module_id: int,
    module_in: schemas.ModuleUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_admin: models.User = Depends(get_current_admin_user)
):
    return await crud.update_module(db, module_id, module_in)

@router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_admin: models.User = Depends(get_current_admin_user)
):
    subject = await db.get(models.Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")
    
    await db.delete(subject)
    await db.commit()
    return {"detail": "Предмет удалён"}

@router.delete("/{module_id}")
async def delete_module(
    module_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_admin: models.User = Depends(get_current_admin_user)
):
    module = await db.get(models.Module, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Модуль не найден")

    await db.delete(module)
    await db.commit()
    return {"detail": "Модуль удалён"}


@router.get("/{module_id}")
async def get_module_details(
    module_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user)
):
    module = await crud.get_module_with_details(db, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Модуль не найден")
    return module


# Предметы (только админ)
@router.post("/{module_id}/subjects", response_model=schemas.Subject)
async def create_subject(
    module_id: int,
    subject_data: schemas.SubjectCreate,
    db: AsyncSession = Depends(get_async_db),
    current_admin: models.User = Depends(get_current_admin_user)
):
    # Проверка: существует ли уже дисциплина с таким названием в этом модуле
    query = select(models.Subject).where(
        models.Subject.module_id == module_id,
        models.Subject.title.ilike(subject_data.title.strip())  # case-insensitive сравнение
    )
    existing = await db.execute(query)
    if existing.first():
        raise HTTPException(status_code=400, detail="Данная дисциплина уже существует в этом модуле")

    # Создание новой дисциплины
    return await crud.create_subject(db, subject_data.title.strip(), module_id)
