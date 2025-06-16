from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_db
from typing import List
from app import schemas, crud, models
from app.utils.auth import get_current_user, get_current_admin_user, get_current_teacher_user

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

# routes/admin/modules.py
@router.post("/{module_id}/subjects", response_model=schemas.Subject)
async def create_subject(
    module_id: int,
    subject_data: schemas.SubjectCreate,
    db: AsyncSession = Depends(get_async_db),
    current_admin: models.User = Depends(get_current_admin_user)
):
    return await crud.create_subject(db, subject_data.title, module_id)

@router.put("/{subject_id}/subjects", response_model=schemas.SubjectUpdate)
async def update_subject(
    subject_id: int,
    subject_in: schemas.SubjectUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_admin: models.User = Depends(get_current_admin_user)
):
    return await crud.update_subject(db, subject_id, subject_in)


# Уроки (только назначенный преподаватель)

@router.post("/subjects/{subject_id}/lessons", response_model=schemas.LessonCreate)
async def add_lesson(
    subject_id: int,
    lesson_in: schemas.LessonCreate,
    db: AsyncSession = Depends(get_async_db),
    current_teacher: models.User = Depends(get_current_teacher_user)
):
    subject = await db.get(models.Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    if subject.teacher_id != current_teacher.id:
        raise HTTPException(status_code=403, detail="Вы не являетесь преподавателем этого предмета")

    return await crud.create_lesson(db, lesson_in, subject_id)

@router.put("/lessons/{lesson_id}", response_model=schemas.LessonUpdate)
async def update_lesson(
    lesson_id: int,
    lesson_in: schemas.LessonUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_teacher: models.User = Depends(get_current_teacher_user)
):
    lesson = await db.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден")

    subject = await db.get(models.Subject, lesson.subject_id)
    if not subject or subject.teacher_id != current_teacher.id:
        raise HTTPException(status_code=403, detail="Вы не можете редактировать этот урок")

    return await crud.update_lesson(db, lesson_id, lesson_in)
