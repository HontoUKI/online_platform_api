from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from sqlalchemy.orm import selectinload
from app.database import get_async_db
from app.utils.auth import get_current_user, get_current_admin_user, get_current_teacher_user
from app.utils import access
from app import crud, models, schemas

router = APIRouter()


@router.get("/access-overview")
async def access_overview(db: AsyncSession = Depends(get_async_db)):
    return await crud.get_access_overview(db)

# Привязка группы к модулю
@router.post("/admin/group-to-module", response_model=schemas.ModuleResponse)
async def add_group_to_module(
    data: schemas.GroupModuleAccessCreate,
    db: AsyncSession = Depends(get_async_db),
    current_admin: models.User = Depends(get_current_admin_user)
):
    return await access.assign_group_to_module(db, data.group_id, data.module_id)


# Привязка преподавателя к предмету
@router.post("/admin/teacher-to-subject", response_model=schemas.SubjectResponse)
async def add_teacher_to_subject(
    data: schemas.TeacherSubjectAccessCreate,
    db: AsyncSession = Depends(get_async_db),
    current_admin: models.User = Depends(get_current_admin_user)
):
    await access.assign_teacher_to_module(db, data.module_id, data.teacher_iin)
    return await access.assign_teacher_to_subject(db, data.subject_id, data.teacher_iin)


# Получить группы, у которых есть доступ к модулю
@router.get("/module/{module_id}/groups", response_model=List[schemas.GroupResponse])
async def get_groups_for_module(
    module_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user)
):
    return await crud.get_groups_for_module(db, module_id)
# Все модули для админа
@router.get("/admin-modules", response_model=List[schemas.ModuleResponse])
async def get_all_modules_for_admin(
    db: AsyncSession = Depends(get_async_db),
    current_admin: models.User = Depends(get_current_admin_user)
):
    result = await db.execute(
        select(models.Module)
        .options(
            selectinload(models.Module.subjects)
            .selectinload(models.Subject.lessons)
        )
    )
    return result.scalars().all()

@router.get("/admin-modules/{module_id}", response_model=schemas.ModuleResponse)
async def get_admin_module_details(
    module_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_admin: models.User = Depends(get_current_admin_user)
):
    module = await db.get(models.Module, module_id)

    if not module:
        raise HTTPException(status_code=404, detail="Модуль не найден")

    # Подгружаем subjects → lessons вручную, чтобы response_model корректно сериализовал
    await db.refresh(module, ["subjects"])
    for subject in module.subjects:
        await db.refresh(subject, ["lessons"])

    return module


# Получить модули, доступные текущему пользователю
@router.get("/my-modules", response_model=List[schemas.ModuleResponse])
async def get_user_modules(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user)
):
    return await crud.get_modules_for_user(db, current_user)

@router.get("/my-modules/{module_id}", response_model=schemas.ModuleResponse)
async def get_module_details(
    module_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user)
):
    module = await crud.get_module_by_id(db, module_id, current_user)
    if not module:
        raise HTTPException(status_code=404, detail="Модуль не найден или доступ запрещён")
    return schemas.ModuleResponse(
        id=module.id,
        title=module.title,
        description=module.description,
        course=module.course,
        created_at=module.created_at,
        subjects=module.subjects
    )

@router.get("/teacher-modules", response_model=List[schemas.ModuleResponse])
async def get_teacher_modules(
    db: AsyncSession = Depends(get_async_db),
    current_teacher: models.User = Depends(get_current_teacher_user)
):
    result = await db.execute(
        select(models.Module).join(models.Subject)
        .filter(models.Subject.teacher_id == current_teacher.id)
        .distinct()
    )
    return result.scalars().all()

@router.get("/teacher-subjects", response_model=List[schemas.SubjectResponse])
async def get_teacher_subjects(
    db: AsyncSession = Depends(get_async_db),
    current_teacher: models.User = Depends(get_current_teacher_user)
):
    result = await db.execute(
        select(models.Subject).where(models.Subject.teacher_id == current_teacher.id)
    )
    return result.scalars().all()

@router.get("/teacher-modules/{module_id}", response_model=schemas.ModuleResponse)
async def get_teacher_module_details(
    module_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_teacher: models.User = Depends(get_current_teacher_user)
):
    module = await crud.get_module_by_teacher(db, module_id, current_teacher)
    if not module:
        raise HTTPException(status_code=404, detail="Модуль не найден или доступ запрещён")

    return module

@router.get("/subjects/{subject_id}/lessons", response_model=List[schemas.LessonResponse])
async def get_lessons(
    subject_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(
        select(models.Lesson).where(models.Lesson.subject_id == subject_id)
    )
    return result.scalars().all()


@router.post("/subjects/{subject_id}/groups/{group_id}")
async def give_access_to_subject(
    subject_id: int, group_id: int, db: AsyncSession = Depends(get_async_db)
):
    return await crud.assign_group_to_subject(db, group_id, subject_id)

@router.delete("/subjects/{subject_id}/groups/{group_id}")
async def remove_access_from_subject(
    subject_id: int, group_id: int, db: AsyncSession = Depends(get_async_db)
):
    return await crud.remove_group_from_subject(db, group_id, subject_id)

@router.get("/lessons/{lesson_id}", response_model=schemas.LessonFull)
async def get_lesson_by_id(
    lesson_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Lesson)
        .where(models.Lesson.id == lesson_id)
        .options(
            selectinload(models.Lesson.subject).selectinload(models.Subject.module),
            selectinload(models.Lesson.results)
        )
    )
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден")

    if not lesson.subject or not lesson.subject.module_id:
        raise HTTPException(status_code=400, detail="Урок не привязан к предмету или модулю")

    lesson.result = next((r for r in lesson.results if r.user_id == current_user.id), None)

    return lesson
