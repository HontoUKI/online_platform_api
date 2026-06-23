from pydantic import BaseModel, Field
from typing import Annotated, List, Optional, Union, Literal
from enum import Enum
from datetime import datetime

# ИИН РК — ровно 12 цифр. Единый тип с валидацией формата.
IIN = Annotated[str, Field(pattern=r"^\d{12}$", description="ИИН: 12 цифр")]

# Пользователи
class PasswordChangeRequest(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)

class UserRole(str, Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"

class UserBase(BaseModel):
    iin: IIN
    full_name: str
    phone: Optional[str] = None
    role: Optional[UserRole] = UserRole.student

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    photo: Optional[str] = None

    class Config:
        from_attributes = True

    @property
    def short_name(self) -> str:
        parts = self.full_name.split()
        if not parts:
            return ""
        initials = [f"{p[0]}." for p in parts[1:] if p]
        return f"{parts[0]} {' '.join(initials)}".strip()

class UserOut(BaseModel):
    id: int
    iin: str
    full_name: Optional[str] = None

    class Config:
        from_attributes = True

class PasswordResetRequest(BaseModel):
    user_iin: IIN
    new_password: str

class PhoneUpdate(BaseModel):
    phone: str

# Авторизация
class LoginRequest(BaseModel):
    iin: IIN
    password: str

# Группы
class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class Group(GroupBase):
    id: int

    class Config:
        from_attributes = True

class GroupUserUpdate(BaseModel):
    user_ids: List[int]

class GroupModuleUpdate(BaseModel):
    module_ids: List[int]

# Уроки
class LessonBase(BaseModel):
    title: str
    type: str  # pdf, video, test
    content_url: str
    

class LessonCreate(LessonBase):
    test_id: Optional[int] = None
    description: Optional[str] = None  
    pass

class LessonUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    content_url: Optional[str] = None

class Lesson(LessonBase):
    id: int

    class Config:
        from_attributes = True

class LessonRead(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True

# Предметы (Subjects)
class SubjectBase(BaseModel):
    title: str

class SubjectCreate(SubjectBase):
    pass

class SubjectUpdate(BaseModel):
    title: Optional[str] = None
    teacher_iin: Optional[str] = None

class Subject(SubjectBase):
    id: int
    lessons: List[Lesson] = []

    class Config:
        from_attributes = True

class SubjectRead(BaseModel):
    id: int
    title: str
    lessons: List[LessonRead]

    class Config:
        from_attributes = True

# Модули
class ModuleBase(BaseModel):
    title: str
    course: Optional[str] = None
    description: Optional[str] = None

class ModuleCreate(ModuleBase):
    pass

class ModuleUpdate(BaseModel):
    title: Optional[str] = None
    course: Optional[str] = None
    description: Optional[str] = None

class Module(ModuleBase):
    id: int
    subjects: List[Subject] = []

    class Config:
        from_attributes = True

class ModuleRead(BaseModel):
    id: int
    title: str
    course: Optional[str] = None
    description: Optional[str] = None
    subjects: List[SubjectRead] = []

    class Config:
        from_attributes = True

# Тесты
class OptionCreate(BaseModel):
    option_text: str
    option_index: int

class QuestionCreate(BaseModel):
    question_text: str
    correct_option_index: int
    options: List[OptionCreate]

class TestBase(BaseModel):
    title: str

class TestCreate(BaseModel):
    title: str
    subject_id: Optional[int] = None
    lesson_id: Optional[int] = None
    questions: List[QuestionCreate]


class Test(TestBase):
    id: int
    subject_id: int
    lesson_id: Optional[int] = None

    class Config:
        from_attributes = True

# Варианты ответа
class OptionBase(BaseModel):
    option_text: str
    option_index: int

class Option(OptionBase):
    id: int

    class Config:
        from_attributes = True

# Вопросы
class QuestionBase(BaseModel):
    question_text: str
    correct_option_index: int


class Question(QuestionBase):
    id: int
    options: List[Option]

    class Config:
        from_attributes = True

# Результаты
class SubmissionCreate(BaseModel):
    comment: Optional[str] = None

class SubmissionOut(BaseModel):
    id: int
    lesson_id: int
    user_id: int
    file_path: str
    comment: Optional[str] = None
    grade: Optional[int]
    student_name: Optional[str] = None
    submitted_at: datetime

    class Config:
        from_attributes = True

class ResultBase(BaseModel):
    score: float

class Answer(BaseModel):
    question_id: int
    selected_index: int

class ResultCreate(BaseModel):
    lesson_id: Optional[int] = None
    test_id: Optional[int] = None
    answers: Optional[List[Answer]] = None

class Result(ResultBase):
    id: int
    user_id: int
    lesson_id: Optional[int] = None
    test_id: Optional[int] = None
    score: Optional[float]
    submitted_at: datetime

    class Config:
        from_attributes = True

class GradeInput(BaseModel):
    grade: int

class GradeSummary(BaseModel):
    submission_id: int
    lesson_id: int
    lesson_title: str
    lesson_type: str
    subject_title: str
    module_title: str
    grade: Optional[int]
    submitted_at: Optional[datetime]
    source: Literal["submission", "test"]

    class Config:
        from_attributes = True

# Доступы
class GroupModuleAccessCreate(BaseModel):
    group_id: int
    module_id: int

class TeacherSubjectAccessCreate(BaseModel):
    teacher_iin: IIN
    module_id: int
    subject_id: int

# Ответы
class GroupResponse(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True

class LessonResponse(BaseModel):
    id: int
    title: str
    description: str
    type: str
    content_url: Optional[str] = None
    subject_id: int
    created_at: datetime
    result: Optional[Result]  = None

    class Config:
        from_attributes = True

class SubjectResponse(BaseModel):
    id: int
    title: str
    module_id: int
    teacher_id: Optional[int] = None
    lessons: List[LessonResponse] = []

    class Config:
        from_attributes = True

class ModuleResponse(BaseModel):
    id: int
    title: str
    course: Optional[str] = None
    description: str
    created_at: datetime
    subjects: List[SubjectResponse] = []

    class Config:
        from_attributes = True

class TestFull(BaseModel):
    id: int
    title: str
    subject_id: int
    lesson_id: Optional[int]
    questions: List[Question]

    class Config:
        from_attributes = True

class TestResultOut(BaseModel):
    id: int
    score: int
    submitted_at: datetime
    student_name: str

    class Config:
        from_attributes = True

class LessonFull(BaseModel):
    id: int
    title: str
    type: str
    description: Optional[str] = None  
    content_url: Optional[str] = None
    subject_id: int
    created_at: datetime

    subject: Optional[SubjectResponse] = None
    result: Optional[Result] = None

    class Config:
        from_attributes = True

class SubjectWithTeacher(BaseModel):
    id: int
    title: str
    teacher: Optional[User] = None
    lessons: List[Lesson] = []

    class Config:
        from_attributes = True

# Модуль с полным деревом
class ModuleWithTeachers(BaseModel):
    id: int
    title: str
    course: int  # если поле есть
    subjects: List[SubjectWithTeacher] = []

    class Config:
        from_attributes = True