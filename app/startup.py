import logging
import os

from app.database import create_tables, SessionLocal
from app.utils.startup_utils import ensure_admin_exists
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("uvicorn.error")

async def on_startup():
    await create_tables()

    # ИИН и пароль администратора обязательны: без явных учётных данных создавать
    # админа с предсказуемым дефолтным паролем небезопасно, поэтому просто пропускаем.
    admin_iin = os.getenv("ADMIN_IIN")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_full_name = os.getenv("ADMIN_FULL_NAME", "Администратор")
    admin_phone = os.getenv("ADMIN_PHONE", "+77000000000")

    if not admin_iin or not admin_password:
        logger.warning(
            "ADMIN_IIN/ADMIN_PASSWORD не заданы — стартовый администратор не создаётся."
        )
        return

    async with SessionLocal() as session:
        await ensure_admin_exists(
            session,
            iin=admin_iin,
            full_name=admin_full_name,
            phone=admin_phone,
            password=admin_password,
        )
