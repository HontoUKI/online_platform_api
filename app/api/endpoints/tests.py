from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.database import get_async_db
from app.utils.auth import get_current_user
from app import models, schemas, crud
from datetime import datetime

router = APIRouter()


# Создание теста
@router.post("/create", response_model=schemas.Test)
async def create_test(test_data: schemas.TestCreate, db: AsyncSession = Depends(get_async_db)):
    test = await crud.create_test_with_questions(db, test_data)
    return test


# Получение одного теста (с вопросами и вариантами)
@router.get("/{test_id}", response_model=schemas.TestFull)
async def get_test(
    test_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user)
):
    # Загружаем тест с вопросами и вариантами
    result = await db.execute(
        select(models.Test)
        .where(models.Test.id == test_id)
        .options(
            selectinload(models.Test.questions).selectinload(models.Question.options)
        )
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден")

    # Подгружаем результат текущего пользователя
    user_result = await db.execute(
        select(models.Result)
        .where(models.Result.test_id == test.id)
        .where(models.Result.user_id == current_user.id)
    )
    test.result = user_result.scalar_one_or_none()  # временно присваиваем на объект

    return test


# Получение всех тестов по subject_id
@router.get("/by-subject/{subject_id}", response_model=list[schemas.Test])
async def get_tests_by_subject(subject_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        select(models.Test).where(models.Test.subject_id == subject_id)
    )
    return result.scalars().all()


# Обновление теста
@router.put("/{test_id}", response_model=schemas.Test)
async def update_test(test_id: int, test_data: schemas.TestCreate, db: AsyncSession = Depends(get_async_db)):
    test = await db.get(models.Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден")

    test.title = test_data.title
    if test_data.subject_id is not None:
       test.subject_id = test_data.subject_id
    if test_data.lesson_id is not None:
       test.lesson_id = test_data.lesson_id

    # Удалим старые вопросы и опции
    await db.execute(delete(models.Option).where(models.Option.question_id.in_(
        select(models.Question.id).where(models.Question.test_id == test.id)
    )))
    await db.execute(delete(models.Question).where(models.Question.test_id == test.id))

    # Добавим обновлённые
    for q in test_data.questions:
        new_q = models.Question(
            test_id=test.id,
            question_text=q.question_text,
            correct_option_index=q.correct_option_index
        )
        db.add(new_q)
        await db.flush()
        for opt in q.options:
            db.add(models.Option(
                question_id=new_q.id,
                option_text=opt.option_text,
                option_index=opt.option_index
            ))

    await db.commit()
    await db.refresh(test)
    return test


# Удаление теста
@router.delete("/{test_id}", status_code=204)
async def delete_test(test_id: int, db: AsyncSession = Depends(get_async_db)):
    test = await db.get(models.Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден")
    await db.delete(test)
    await db.commit()

# Завершить тест
@router.post("/submit", response_model=schemas.Result)
async def submit_test(
    result_data: schemas.ResultCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user)
):
    test = await db.get(models.Test, result_data.test_id)
    if not result_data.answers:
        raise HTTPException(status_code=400, detail="Нет ответов на тест")

    if not isinstance(result_data.answers, list):
        raise HTTPException(status_code=400, detail="Неверный формат данных answers")

    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден")

    if not test.lesson_id:
        raise HTTPException(status_code=400, detail="Тест не привязан к уроку")

    result = await db.execute(
        select(models.Question)
        .where(models.Question.test_id == result_data.test_id)
        .options(selectinload(models.Question.options))
    )
    questions = result.scalars().all()

    if not questions:
        raise HTTPException(status_code=400, detail="У теста нет вопросов")

    correct = 0
    for q in questions:
        answer = next((a for a in result_data.answers or [] if a.question_id == q.id), None)
        if answer and answer.selected_index == q.correct_option_index:
            correct += 1

    # Проверяем, есть ли уже результат
    existing_result = await db.execute(
    select(models.Result)
    .where(models.Result.test_id == test.id)
    .where(models.Result.user_id == current_user.id)
    )
    if existing_result.scalars().first():
        raise HTTPException(status_code=400, detail="Вы уже проходили этот тест")

    total = len(questions)
    score = round((correct / total) * 100, 2)

    new_result = models.Result(
        user_id=current_user.id,
        lesson_id=test.lesson_id,
        test_id=test.id,
        score=score,
        submitted_at=datetime.utcnow()
    )
    db.add(new_result)
    await db.commit()
    await db.refresh(new_result)
    return new_result
