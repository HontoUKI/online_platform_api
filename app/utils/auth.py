from datetime import datetime, timedelta, timezone
from typing import Union
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import os
from dotenv import load_dotenv
from app.database import async_session
from app.models import User, UserRole

load_dotenv()

# SECRET_KEY обязателен: без него подпись токенов небезопасна, поэтому падаем на старте,
# а не молча используем предсказуемый дефолт.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY не задан в переменных окружения")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Контекст хеширования
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 схема
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Хеширование и проверка паролей
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Генерация токена
def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Получение пользователя из токена
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        iin: str = payload.get("sub")
        if not iin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Вы не авторизованы")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Вы не авторизованы")

    async with async_session() as db:
        result = await db.execute(select(User).where(User.iin == iin))
        user = result.scalars().first()

        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
        return user

def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ воспрещен: только для администраторов")
    return current_user

def get_current_teacher_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.teacher, UserRole.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ воспрещен: только для преподавателей")
    return current_user

def get_current_student_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.student:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ воспрещен: только для студентов")
    return current_user
