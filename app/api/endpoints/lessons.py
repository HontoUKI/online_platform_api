from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
import os

from app.database import get_async_db
from app.utils.auth import get_current_user, get_current_teacher_user
from app import models, schemas

router = APIRouter()

@router.post("/add/subjects/{subject_id}", response_model=schemas.LessonResponse)
async def add_lesson(
    subject_id: int,
    lesson_data: schemas.LessonCreate,
    db: AsyncSession = Depends(get_async_db),
    current_teacher: models.User = Depends(get_current_teacher_user)
):
    subject = await db.get(models.Subject, subject_id)
    if not subject or subject.teacher_id != current_teacher.id:
        raise HTTPException(status_code=403, detail="Нет доступа к предмету")

    lesson_dict = lesson_data.dict()
    lesson_dict.pop("test_id", None)
    lesson = models.Lesson(**lesson_dict, subject_id=subject_id)

    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)

    if lesson_data.type == "test" and lesson_data.test_id:
        test = await db.get(models.Test, lesson_data.test_id)
        if not test:
            raise HTTPException(status_code=404, detail="Тест не найден")
        test.lesson_id = lesson.id
        await db.commit()

    return lesson

@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_teacher=Depends(get_current_teacher_user)
):
    lesson = await db.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден")

    subject = await db.get(models.Subject, lesson.subject_id)
    if not subject or subject.teacher_id != current_teacher.id:
        raise HTTPException(status_code=403, detail="Нет доступа к предмету")

    # Удалим связанные файлы
    homework_folder = f"static/homework/lesson_{lesson_id}"
    doc_path = lesson.content_url if lesson.content_url and lesson.content_url.startswith("/static/lesson_docs/") else None

    import shutil, os
    if os.path.isdir(homework_folder):
        shutil.rmtree(homework_folder)
    if doc_path and os.path.isfile(doc_path[1:]):
        os.remove(doc_path[1:])

    await db.delete(lesson)
    await db.commit()
    return {"detail": "Урок успешно удалён"}


@router.get("/{lesson_id}", response_model=schemas.LessonResponse)
async def get_lesson(
    lesson_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Lesson)
        .options(selectinload(models.Lesson.subject).selectinload(models.Subject.module))
        .where(models.Lesson.id == lesson_id)
    )
    lesson = result.scalars().first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден или доступ запрещён")

    res_result = await db.execute(
        select(models.Result)
        .where(models.Result.lesson_id == lesson.id)
        .where(models.Result.user_id == current_user.id)
        .order_by(models.Result.submitted_at.desc())
        .limit(1)
    )
    lesson.result = res_result.scalar_one_or_none()
    return lesson

@router.post("/upload/lesson-file")
async def upload_lesson_file(
    file: UploadFile = File(...),
    current_teacher=Depends(get_current_teacher_user)
):
    folder = "static/lesson_docs"
    os.makedirs(folder, exist_ok=True)

    ext = os.path.splitext(file.filename)[-1]
    file_name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(folder, file_name)

    try:
        with open(path, "wb") as f:
            f.write(await file.read())
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка при сохранении файла")

    return {"url": f"/{path}"}


@router.post("/{lesson_id}/submit-homework")
async def submit_homework(
    lesson_id: int,
    file: UploadFile = File(...),
    comment: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user)
):
    lesson = await db.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден")

    folder = f"static/homework/lesson_{lesson_id}"
    os.makedirs(folder, exist_ok=True)

    ext = os.path.splitext(file.filename)[-1]
    file_name = f"{current_user.id}_{datetime.utcnow().timestamp():.0f}{ext}"
    file_path = os.path.join(folder, file_name)

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка при сохранении файла")

    submission = models.LessonSubmission(
        lesson_id=lesson_id,
        user_id=current_user.id,
        comment=comment,
        file_path=file_path,
        submitted_at=datetime.utcnow()
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    return {"detail": "Файл успешно загружен", "file": file_name}


@router.get("/{lesson_id}/submissions/files", response_model=List[schemas.SubmissionOut])
async def get_lesson_file_submissions(
    lesson_id: int,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_teacher=Depends(get_current_teacher_user)
):
    lesson = await db.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, detail="Урок не найден")

    subject = await db.get(models.Subject, lesson.subject_id)
    if not subject or subject.teacher_id != current_teacher.id:
        raise HTTPException(403, detail="Нет доступа к уроку")

    result = await db.execute(
        select(models.LessonSubmission)
        .options(selectinload(models.LessonSubmission.user))
        .where(models.LessonSubmission.lesson_id == lesson_id)
    )
    submissions = result.scalars().all()

    if search:
        search_lower = search.lower()
        submissions = [
            s for s in submissions
            if search_lower in (s.user.full_name or "").lower()
        ]

    for s in submissions:
        s.student_name = s.user.full_name

    return submissions


@router.get("/{lesson_id}/submissions/tests", response_model=List[schemas.TestResultOut])
async def get_lesson_test_results(
    lesson_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_teacher=Depends(get_current_teacher_user)
):
    lesson = await db.get(models.Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, detail="Урок не найден")

    subject = await db.get(models.Subject, lesson.subject_id)
    if not subject or subject.teacher_id != current_teacher.id:
        raise HTTPException(403, detail="Нет доступа к уроку")

    result = await db.execute(
        select(models.Result)
        .options(selectinload(models.Result.user))
        .where(models.Result.lesson_id == lesson_id)
    )
    results = result.scalars().all()

    for r in results:
        r.student_name = r.user.full_name

    return results

@router.get("/{lesson_id}/my-submissions", response_model=List[schemas.SubmissionOut])
async def get_my_submissions(
    lesson_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(
        select(models.LessonSubmission)
        .where(models.LessonSubmission.lesson_id == lesson_id)
        .where(models.LessonSubmission.user_id == current_user.id)
        .order_by(models.LessonSubmission.submitted_at.desc())
    )
    return result.scalars().all()

@router.delete("/submission/{submission_id}")
async def delete_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user)
):
    submission = await db.get(models.LessonSubmission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Работа не найдена")

    # Проверка: студент может удалять только свою работу
    if submission.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    # Удалим файл
    if submission.file_path and os.path.exists(submission.file_path):
        os.remove(submission.file_path)

    await db.delete(submission)
    await db.commit()

    return {"detail": "Работа удалена"}

@router.delete("/result/{result_id}")
async def delete_test_result(
    result_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_teacher=Depends(get_current_teacher_user)
):
    result = await db.get(models.Result, result_id)
    if not result:
        raise HTTPException(404, detail="Результат не найден")

    lesson = await db.get(models.Lesson, result.lesson_id)
    if not lesson:
        raise HTTPException(403, detail="Нет доступа")

    subject = await db.get(models.Subject, lesson.subject_id)
    if not subject or subject.teacher_id != current_teacher.id:
        raise HTTPException(403, detail="Нет доступа к удалению")

    await db.delete(result)
    await db.commit()

    return {"detail": "Результат удалён"}


@router.patch("/submission/{submission_id}/grade")
async def grade_submission(
    submission_id: int,
    data: schemas.GradeInput,
    db: AsyncSession = Depends(get_async_db),
    current_teacher=Depends(get_current_teacher_user)
):
    submission = await db.get(models.LessonSubmission, submission_id)
    if not submission:
        raise HTTPException(404, detail="Работа не найдена")

    lesson = await db.get(models.Lesson, submission.lesson_id)
    subject = await db.get(models.Subject, lesson.subject_id)
    if not subject or subject.teacher_id != current_teacher.id:
        raise HTTPException(status_code=403, detail="Нет доступа к оценке")

    submission.grade = data.grade
    await db.commit()
    return {"detail": "Оценка сохранена"}

@router.get("/student/grades", response_model=List[schemas.GradeSummary])
async def get_student_grades(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user)
):
    # Домашние задания
    homework_query = select(models.LessonSubmission).options(
        selectinload(models.LessonSubmission.lesson)
        .selectinload(models.Lesson.subject)
        .selectinload(models.Subject.module)
    ).where(models.LessonSubmission.user_id == current_user.id)

    homework_result = await db.execute(homework_query)
    homework = homework_result.scalars().all()

    # Тесты
    test_query = select(models.Result).options(
        selectinload(models.Result.lesson)
        .selectinload(models.Lesson.subject)
        .selectinload(models.Subject.module)
    ).where(models.Result.user_id == current_user.id)

    test_result = await db.execute(test_query)
    tests = test_result.scalars().all()

    # Объединяем оба списка
    summary = []

    for h in homework:
        summary.append({
            "submission_id": h.id,
            "lesson_id": h.lesson.id,
            "lesson_title": h.lesson.title,
            "lesson_type": h.lesson.type,
            "subject_title": h.lesson.subject.title,
            "module_title": h.lesson.subject.module.title,
            "grade": h.grade,
            "submitted_at": h.submitted_at,
            "source": "submission"
        })

    for t in tests:
        summary.append({
            "submission_id": t.id,
            "lesson_id": t.lesson.id,
            "lesson_title": t.lesson.title,
            "lesson_type": "тест",
            "subject_title": t.lesson.subject.title,
            "module_title": t.lesson.subject.module.title,
            "grade": t.score,
            "submitted_at": t.submitted_at,
            "source": "test"
        })

    return summary
