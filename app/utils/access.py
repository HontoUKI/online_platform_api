from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.crud import get_user_by_iin
from app.models import UserRole
from app import models


async def has_access_to_module(db: AsyncSession, user: models.User, module_id: int) -> bool:
    if user.role == UserRole.admin:
        return True

    # Получить модуль с группами и предметами
    result = await db.execute(
        select(models.Module)
        .options(
            selectinload(models.Module.groups),
            selectinload(models.Module.subjects)
        )
        .where(models.Module.id == module_id)
    )
    module = result.scalar_one_or_none()

    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Проверка доступа по группам
    user_group_ids = {group.id for group in user.groups}
    module_group_ids = {group.id for group in module.groups}
    if user_group_ids.intersection(module_group_ids):
        return True

    # Преподаватель модуля имеет доступ через предметы
    if user.role == UserRole.teacher:
        for subject in module.subjects:
            if subject.teacher_id == user.id:
                return True

    return False


async def can_edit_module(db: AsyncSession, user: models.User, module_id: int) -> bool:
    if user.role == UserRole.admin:
        return True

    result = await db.execute(
        select(models.Module)
        .options(selectinload(models.Module.subjects))
        .where(models.Module.id == module_id)
    )
    module = result.scalar_one_or_none()

    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    if user.role == UserRole.teacher:
        for subject in module.subjects:
            if subject.teacher_id == user.id:
                return True

    return False


async def assign_group_to_module(db: AsyncSession, group_id: int, module_id: int) -> models.Module:
    group_result = await db.execute(
        select(models.Group).where(models.Group.id == group_id)
    )
    group = group_result.scalar_one_or_none()

    module_result = await db.execute(
        select(models.Module)
        .options(selectinload(models.Module.groups))
        .where(models.Module.id == module_id)
    )
    module = module_result.scalar_one_or_none()

    if not group or not module:
        raise HTTPException(status_code=404, detail="Группа или Модуль не найдены")

    if group not in module.groups:
        module.groups.append(group)
        await db.commit()
        await db.refresh(module)

    return module

async def assign_teacher_to_module(db: AsyncSession, module_id: int, teacher_iin: int) -> models.Module:
    module_result = await db.execute(
        select(models.Module)
        .options(selectinload(models.Module.groups))
        .where(models.Module.id == module_id)
    )
    module = module_result.scalar_one_or_none()

    teacher_result = await db.execute(
        select(models.User).where(models.User.iin == teacher_iin)
    )
    teacher = teacher_result.scalar_one_or_none()


    if not module or not teacher:
        raise HTTPException(status_code=404, detail="Дисциплина или Преподаватель не найдены")

    if teacher.role != UserRole.teacher:
        raise HTTPException(status_code=400, detail="Пользователь не является преподавателем")

    if teacher not in module.teachers:
        module.teachers.append(teacher)
        await db.commit()
        await db.refresh(module)

    return teacher

async def assign_teacher_to_subject(db: AsyncSession, subject_id: int, teacher_iin: str) -> models.Subject:
    subject = await db.get(models.Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    teacher = await get_user_by_iin(db, teacher_iin)
    if not teacher:
        raise HTTPException(status_code=404, detail="Преподаватель не найден")

    if teacher.role != UserRole.teacher:
        raise HTTPException(status_code=400, detail="Пользователь не является преподавателем")

    subject.teacher_id = teacher.id

    await db.commit()
    await db.refresh(subject)

    return subject



async def check_user_access_to_module(db: AsyncSession, user: models.User, module_id: int) -> bool:
    if user.role == UserRole.admin:
        return True

    # Получить ID групп пользователя
    group_ids = [group.id for group in user.groups]

    result = await db.execute(
        select(models.Module)
        .join(models.Module.groups)
        .where(models.Module.id == module_id, models.Group.id.in_(group_ids))
    )

    module = result.scalars().first()
    return module is not None
