from app.database import create_tables, SessionLocal
from app.utils.startup_utils import ensure_admin_exists
from dotenv import load_dotenv
import os

load_dotenv()

async def on_startup():
    await create_tables()

    admin_iin = os.getenv("ADMIN_IIN", "000000000000")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    admin_full_name = os.getenv("ADMIN_FULL_NAME", "Администратор")
    admin_phone = os.getenv("ADMIN_PHONE", "+77000000000")

    async with SessionLocal() as session:
        await ensure_admin_exists(
            session,
            iin=admin_iin,
            full_name=admin_full_name,
            phone=admin_phone,
            password=admin_password,
        )
