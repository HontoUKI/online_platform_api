from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import NoResultFound, IntegrityError
from typing import List, Optional

from app import models, schemas
from app.utils.auth import get_password_hash

# Пользователи
# Асинхронное получение пользователя по IIN
async def get_user_by_iin(db: AsyncSession, iin: str) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.iin == iin))
    return result.scalars().first()

async def get_user_by_phone(db: AsyncSession, phone: str) -> Optional[models.User] | None:
    result = await db.execute(
        select(models.User).where(models.User.phone == phone)
    )
    return result.scalar_one_or_none()

# Асинхронное создание пользователя с хешированием пароля
async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    existing = await db.execute(select(models.User).where(models.User.iin == user.iin))
    if existing.scalar():
        raise HTTPException(status_code=400, detail="Пользователь с таким ИИН уже существует")

    db_user = models.User(
        iin=user.iin,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        hashed_password=get_password_hash(user.password),
    )
    db.add(db_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка создания пользователя")

    await db.refresh(db_user)
    return db_user

# Асинхронное обновление пароля пользователя
async def update_user_password(db: AsyncSession, user: models.User, new_password: str):
    user.hashed_password = get_password_hash(new_password)
    db.add(user)
    await db.commit()   

# Модули
async def get_modules(db: AsyncSession) -> List[models.Module]:
    result = await db.execute(select(models.Module))
    return result.scalars().all()

async def get_module_with_details(db: AsyncSession, module_id: int) -> models.Module | None:
    result = await db.execute(
        select(models.Module)
        .options(
            selectinload(models.Module.subjects).selectinload(models.Subject.lessons)
        )
        .where(models.Module.id == module_id)
    )
    return result.scalars().first()

async def get_modules_with_teachers(db: AsyncSession) -> List[models.Module]:
    result = await db.execute(
        select(models.Module)
        .options(
            selectinload(models.Module.subjects)
            .selectinload(models.Subject.teacher),  # преподаватели
            selectinload(models.Module.subjects)
            .selectinload(models.Subject.lessons)   # уроки
        )
    )
    return result.scalars().all()


async def create_module(db: AsyncSession, module_in: schemas.ModuleCreate) -> models.Module:
    db_module = models.Module(
        title=module_in.title,
        course=module_in.course,
        description=module_in.description,
    )
    db.add(db_module)
    await db.commit()
    await db.refresh(db_module)
    return db_module

async def update_module(db: AsyncSession, module_id: int, module_in: schemas.ModuleUpdate) -> models.Module:
    db_module = await db.get(models.Module, module_id)
    if not db_module:
        raise HTTPException(status_code=404, detail="Модуль не найден")

    for field, value in module_in.dict(exclude_unset=True).items():
        setattr(db_module, field, value)

    await db.commit()
    await db.refresh(db_module)
    return db_module

# Создание предмета
async def create_subject(db: AsyncSession,  title: str,  module_id: int):
    subject = models.Subject(
        title=title,
        module_id=module_id
    )
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return subject

# Обновление предмета
async def update_subject(db: AsyncSession, subject_id: int, subject_in: schemas.SubjectUpdate):
    subject = await db.get(models.Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    update_data = subject_in.dict(exclude_unset=True)
    if "teacher_iin" in update_data:
        teacher_result = await db.execute(select(models.User).where(models.User.iin == update_data["teacher_iin"]))
        teacher = teacher_result.scalars().first()
        if not teacher or teacher.role != "teacher":
            raise HTTPException(status_code=404, detail="Преподаватель с таким ИИН не найден")
        update_data["teacher_id"] = teacher.id
        del update_data["teacher_iin"]

    for field, value in update_data.items():
        setattr(subject, field, value)

    await db.commit()
    await db.refresh(subject)
    return subject


# Группы
async def get_all_groups(db: AsyncSession) -> List[models.Group]:
    result = await db.execute(select(models.Group))
    return result.scalars().all()

async def get_group_by_id(db: AsyncSession, group_id: int) -> models.Group:
    result = await db.execute(select(models.Group).where(models.Group.id == group_id))
    group = result.scalars().first()
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    return group


async def create_group(db: AsyncSession, group: schemas.GroupCreate) -> models.Group:
    db_group = models.Group(name=group.name, description=group.description)
    db.add(db_group)
    await db.commit()
    await db.refresh(db_group)
    return db_group

async def add_users_to_group(db: AsyncSession, group_id: int, user_ids: List[int]) -> models.Group:
    group = await get_group_by_id(db, group_id)

    for user_id in user_ids:
        user_result = await db.execute(select(models.User).where(models.User.id == user_id))
        user = user_result.scalars().first()
        if user and user not in group.users:
            group.users.append(user)

    await db.commit()
    await db.refresh(group)
    return group

async def get_group_users(db: AsyncSession, group_id: int) -> List[models.User]:
    group = await get_group_by_id(db, group_id)
    return group.users


async def remove_user_from_group(db: AsyncSession, group_id: int, user_id: int) -> models.Group:
    group = await get_group_by_id(db, group_id)

    user_result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = user_result.scalars().first()
    if user and user in group.users:
        group.users.remove(user)

    await db.commit()
    await db.refresh(group)
    return group


# Уроки
async def get_lessons_by_module(db: AsyncSession, module_id: int) -> List[models.Lesson]:
    result = await db.execute(
        select(models.Lesson)
        .where(models.Lesson.module_id == module_id)
        .options(selectinload(models.Lesson.subject))
    )
    return result.scalars().all()

# Тестирования, вопросы и тп.
async def create_test_with_questions(db: AsyncSession, test_data: schemas.TestCreate) -> models.Test:
    db_test = models.Test(title=test_data.title, lesson_id=test_data.lesson_id, subject_id=test_data.subject_id)
    db.add(db_test)
    await db.flush()

    for q in test_data.questions:
        db_question = models.Question(
            test_id=db_test.id,
            question_text=q.question_text,
            correct_option_index=q.correct_option_index
        )
        db.add(db_question)
        await db.flush()
        for opt in q.options:
            db_option = models.Option(
                question_id=db_question.id,
                option_text=opt.option_text,
                option_index=opt.option_index
            )
            db.add(db_option)

    await db.commit()
    await db.refresh(db_test)
    return db_test

async def update_test_with_questions(db: AsyncSession, test_id: int, test_data: schemas.TestCreate) -> models.Test:
    test = await db.get(models.Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден")

    test.title = test_data.title
    test.subject_id = test_data.subject_id
    test.lesson_id = test_data.lesson_id

    await db.execute(delete(models.Option).where(models.Option.question_id.in_(
        select(models.Question.id).where(models.Question.test_id == test.id)
    )))
    await db.execute(delete(models.Question).where(models.Question.test_id == test.id))

    for q in test_data.questions:
        question = models.Question(
            test_id=test.id,
            question_text=q.question_text,
            correct_option_index=q.correct_option_index
        )
        db.add(question)
        await db.flush()
        for opt in q.options:
            option = models.Option(
                question_id=question.id,
                option_text=opt.option_text,
                option_index=opt.option_index
            )
            db.add(option)

    await db.commit()
    await db.refresh(test)
    return test

async def save_result(db: AsyncSession, result_data: schemas.ResultCreate) -> models.Result:
    db_result = models.Result(
        user_id=result_data.user_id,
        lesson_id=result_data.lesson_id,
        test_id=result_data.test_id,
        score=result_data.score,
        submitted_at=result_data.submitted_at
    )
    db.add(db_result)
    await db.commit()
    await db.refresh(db_result)
    return db_result

# Доступ групп к модулям
async def assign_group_to_module(db: AsyncSession, group_id: int, module_id: int) -> models.Module:
    module = await db.get(models.Module, module_id)
    group = await db.get(models.Group, group_id)

    if not module or not group:
        raise HTTPException(status_code=404, detail="Группа или модуль не найдены")

    if group.id not in [g.id for g in module.groups]:  # Проверка дублирования
        module.groups.append(group)
        await db.commit()
        await db.refresh(module)

    return module

async def assign_group_to_subject(db: AsyncSession, group_id: int, subject_id: int) -> models.Subject:
    subject = await db.get(models.Subject, subject_id)
    group = await db.get(models.Group, group_id)

    if not subject or not group:
        raise HTTPException(status_code=404, detail="Группа или предмет не найдены")

    if group.id not in [g.id for g in subject.groups]:  # Проверка дублирования
        subject.groups.append(group)
        await db.commit()
        await db.refresh(subject)

    return subject

# Доступ преподавателя к предмету
async def assign_teacher_to_subject(db: AsyncSession, subject_id: int, teacher_id: int) -> models.Subject:
    subject = await db.get(models.Subject, subject_id)
    teacher = await db.get(models.User, teacher_id)

    if not subject or not teacher:
        raise HTTPException(status_code=404, detail="Предмет или преподаватель не найдены")

    if teacher.role != models.UserRole.teacher:
        raise HTTPException(status_code=400, detail="Пользователь не является преподавателем")

    if subject.teacher_id != teacher.id:  # Проверка, назначен ли уже преподаватель
        subject.teacher_id = teacher.id
        await db.commit()
        await db.refresh(subject)

    return subject

# Получение модулей, доступных пользователю
async def get_modules_for_user(db: AsyncSession, user: models.User) -> List[models.Module]:
    if user.role == models.UserRole.admin:
        result = await db.execute(select(models.Module))
        return result.scalars().all()

    # Для студентов и преподавателей — через группы. Перечитываем пользователя с
    # явной загрузкой групп, чтобы не зависеть от состояния переданной сессии.
    user = await db.get(models.User, user.id, options=[selectinload(models.User.groups)])
    group_ids = [group.id for group in user.groups]

    result = await db.execute(
        select(models.Module)
        .join(models.Module.groups)
        .filter(models.Group.id.in_(group_ids))
        .distinct()
    )
    return result.scalars().all()

# Получение дисциплин, доступных пользователю
async def get_subjects_for_user(db: AsyncSession, user: models.User) -> List[models.Subject]:
    if user.role == models.UserRole.admin:
        result = await db.execute(select(models.Subject))
        return result.scalars().all()

    elif user.role == models.UserRole.teacher:
        result = await db.execute(
            select(models.Subject).where(models.Subject.teacher_id == user.id)
        )
        return result.scalars().all()

    elif user.role == models.UserRole.student:
        user = await db.get(models.User, user.id, options=[selectinload(models.User.groups)])
        group_ids = [group.id for group in user.groups]

        result = await db.execute(
            select(models.Subject)
            .join(models.Module)
            .join(models.Module.groups)
            .filter(models.Group.id.in_(group_ids))
            .distinct()
        )
        return result.scalars().all()

    return []

async def remove_group_from_subject(db: AsyncSession, group_id: int, subject_id: int) -> models.Subject:
    subject = await db.get(models.Subject, subject_id)
    group = await db.get(models.Group, group_id)

    if not subject or not group:
        raise HTTPException(status_code=404, detail="Группа или предмет не найдены")

    if group.id in [g.id for g in subject.groups]:  # Удаление только если есть доступ
        subject.groups.remove(group)
        await db.commit()
        await db.refresh(subject)

    return subject

async def get_groups_for_subject(db: AsyncSession, subject_id: int) -> List[models.Group]:
    result = await db.execute(
        select(models.Subject)
        .options(selectinload(models.Subject.groups))
        .where(models.Subject.id == subject_id)
    )
    subject = result.scalars().first()

    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    return subject.groups

# Получение групп, у которых есть доступ к модулю
async def get_groups_for_module(db: AsyncSession, module_id: int) -> List[models.Group]:
    result = await db.execute(
        select(models.Module).options(selectinload(models.Module.groups)).where(models.Module.id == module_id)
    )
    module = result.scalars().first()

    if not module:
        raise HTTPException(status_code=404, detail="Модуль не найден")

    return module.groups

async def get_module_by_id(db: AsyncSession, module_id: int, user: models.User) -> Optional[models.Module]:
    result = await db.execute(
        select(models.Module)
        .where(models.Module.id == module_id)
        .options(
            selectinload(models.Module.subjects)
            .selectinload(models.Subject.lessons)
            .selectinload(models.Lesson.results)
        )
    )
    module = result.scalar_one_or_none()

    if not module:
        return None

    # В каждый урок подставляем result вручную
    for subject in module.subjects:
        for lesson in subject.lessons:
            lesson.result = next(
                (res for res in lesson.results if res.user_id == user.id),
                None
            )

    return module

async def get_module_by_teacher(db: AsyncSession, module_id: int, teacher: models.User):
    result = await db.execute(
        select(models.Module)
        .options(
            selectinload(models.Module.subjects),
            selectinload(models.Module.groups)
        )
        .join(models.Module.teachers)
        .where(models.Module.id == module_id, models.User.id == teacher.id)
    )
    return result.scalars().first()

# Получение общей информации о доступе групп к модулям и предметам
async def get_access_overview(db: AsyncSession) -> dict:
    result = await db.execute(
        select(models.Module)
        .options(
            selectinload(models.Module.groups),
            selectinload(models.Module.subjects).selectinload(models.Subject.teacher)
        )
    )
    modules = result.scalars().all()

    overview = []

    for module in modules:
        module_info = {
            "module_id": module.id,
            "module_title": module.title,
            "groups": [{"id": group.id, "name": group.name} for group in module.groups],
            "subjects": []
        }

        for subject in module.subjects:
            module_info["subjects"].append({
                "subject_id": subject.id,
                "title": subject.title,
                "teacher": {
                    "id": subject.teacher.id,
                    "full_name": subject.teacher.full_name
                } if subject.teacher else None
            })

        overview.append(module_info)

    return {"modules": overview}