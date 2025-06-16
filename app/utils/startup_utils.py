from app.schemas import UserCreate
from app.crud import get_user_by_iin, create_user

async def ensure_admin_exists(
    db_session,
    iin: str,
    full_name: str,
    phone: str,
    password: str,
):
    existing_admin = await get_user_by_iin(db_session, iin)
    if not existing_admin:
        user_data = UserCreate(
            iin=iin,
            full_name=full_name,
            phone=phone,
            password=password,
            role="admin"
        )
        await create_user(db_session, user_data)
        print("Администратор создан.")
    else:
        print("Администратор уже существует.")
