from sqlalchemy import (
    Column, Integer, String, ForeignKey, Boolean, Text, DateTime,
    Table, Enum, Float
)
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

# Ассоциации для многие-ко-многим
user_group_table = Table(
    "user_group",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
)

module_group_table = Table(
    "module_group",
    Base.metadata,
    Column("module_id", Integer, ForeignKey("modules.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
)
teacher_module_table = Table(
    "teacher_module",
    Base.metadata,
    Column("module_id", Integer, ForeignKey("modules.id"), primary_key=True),
    Column("teacher_id", Integer, ForeignKey("users.id"), primary_key=True),
)


# Перечисление ролей
class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    iin = Column(String(12), unique=True, index=True, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.student, nullable=False)
    phone = Column(String(20), nullable=True, unique=True)
    hashed_password = Column(String(255), nullable=False)
    photo = Column(String(255), nullable=True)

    teaching_modules = relationship("Module", secondary=teacher_module_table, back_populates="teachers", lazy='selectin')
    groups = relationship("Group", secondary=user_group_table, back_populates="users", lazy='selectin')
    results = relationship("Result", back_populates="user", lazy='selectin')

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    users = relationship("User", secondary=user_group_table, back_populates="groups", lazy='selectin')
    modules = relationship("Module", secondary=module_group_table, back_populates="groups", lazy='selectin')

class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    course = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)  

    teachers = relationship("User", secondary=teacher_module_table, back_populates="teaching_modules", lazy='selectin')
    subjects = relationship("Subject", back_populates="module", cascade="all, delete-orphan", lazy='selectin')
    groups = relationship("Group", secondary=module_group_table, back_populates="modules", lazy='selectin')

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(100), nullable=False)

    tests = relationship("Test", back_populates="subject", cascade="all, delete-orphan", lazy='selectin')
    module = relationship("Module", back_populates="subjects", lazy='selectin')
    lessons = relationship("Lesson", back_populates="subject", cascade="all, delete-orphan", lazy='selectin')

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # video, pdf, test
    description = Column(Text, nullable=True)
    content_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    submissions = relationship("LessonSubmission", back_populates="lesson", cascade="all, delete-orphan")
    subject = relationship("Subject", back_populates="lessons", lazy='selectin')
    test = relationship("Test", back_populates="lesson", uselist=False, lazy='selectin')
    results = relationship("Result", back_populates="lesson", lazy='selectin')

class LessonSubmission(Base):
    __tablename__ = "lesson_submissions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    file_path = Column(String(512), nullable=False)
    comment = Column(Text, nullable=True)
    grade = Column(Integer, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    lesson = relationship("Lesson", back_populates="submissions")
    user = relationship("User")

class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), unique=True)

    subject = relationship("Subject", back_populates="tests", lazy='selectin')
    lesson = relationship("Lesson", back_populates="test", lazy='selectin')
    questions = relationship("Question", back_populates="test", cascade="all, delete-orphan", lazy='selectin')

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    correct_option_index = Column(Integer, nullable=False)

    test = relationship("Test", back_populates="questions", lazy='selectin')
    options = relationship("Option", back_populates="question", cascade="all, delete-orphan", lazy='selectin')

class Option(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    option_text = Column(Text, nullable=False)
    option_index = Column(Integer, nullable=False)

    question = relationship("Question", back_populates="options", lazy='selectin')

class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=True)
    score = Column(Float, nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="results", lazy='selectin')
    lesson = relationship("Lesson", back_populates="results", lazy='selectin')

