from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud, schemas
from app.database import get_async_db
from app.utils.auth import verify_password, create_access_token

router = APIRouter()

@router.post("/login")
async def login(request: schemas.LoginRequest, db: AsyncSession = Depends(get_async_db)):
    user = await crud.get_user_by_iin(db, request.iin)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect IIN or password")
    
    await db.refresh(user)
    
    print("Plain:", request.password)
    print("Hashed:", user.hashed_password)
    print("Match:", verify_password(request.password, user.hashed_password))

    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect IIN or password")

    access_token = create_access_token(data={"sub": user.iin})

    # Формируем ответ с данными пользователя (можно использовать pydantic-схему User)
    user_data = schemas.User.from_orm(user)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "iin": user_data.iin,
            "role": user_data.role,
            "phone": user_data.phone,
            "photo": user_data.photo,
            "full_name": user_data.full_name,
            "short_name": user_data.short_name,
        }
    }
