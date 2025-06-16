from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud, schemas
from app.database import get_async_db

router = APIRouter()

@router.post("/register", response_model=schemas.User)
async def register_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_async_db)):
    db_user = await crud.get_user_by_iin(db, user.iin)
    if db_user:
        raise HTTPException(status_code=400, detail="Данный пользователь уже зарегистрирован")
    return await crud.create_user(db, user)
