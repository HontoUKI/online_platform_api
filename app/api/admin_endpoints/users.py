from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_db
from app.utils.auth import get_current_admin_user
from app.schemas import UserCreate, User, PasswordResetRequest
from app.crud import create_user, get_user_by_iin, update_user_password

router = APIRouter(tags=["admin_users"])

@router.post("/", response_model=User)
async def admin_create_user(
    user_iin: UserCreate,
    db: AsyncSession = Depends(get_async_db),
    current_admin=Depends(get_current_admin_user),
):
    user = await create_user(db, user_iin)
    return user

@router.patch("/reset_password")
async def admin_change_user_password(
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(get_async_db),
    current_admin=Depends(get_current_admin_user),
):
    user = await get_user_by_iin(db, payload.user_iin)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await update_user_password(db, user, payload.new_password)
