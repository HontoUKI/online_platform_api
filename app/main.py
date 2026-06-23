import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from os import getenv

from app.startup import on_startup

from app.api.endpoints.login import router as login_router
from app.api.admin_endpoints.users import router as admin_user_router
from app.api.admin_endpoints.groups import router as admin_groups_router
from app.api.admin_endpoints.modules import router as admin_modules_router
from app.api.endpoints.lessons import router as lessons_router
from app.api.endpoints.tests import router as tests_router
from app.api.endpoints.access import router as access_router
from app.api.endpoints.user import router as users_router
from app.api.endpoints.files import router as files_router


from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("uvicorn.error")

PLACE_URL = getenv("PLACE_URL", "").strip().strip('"').strip("'")
allow_origins = (
    ["*"] if not PLACE_URL else [url.strip() for url in PLACE_URL.split(",")]
)

# Браузеры запрещают связку wildcard-origin + credentials, поэтому при пустом PLACE_URL
# отключаем передачу cookie/Authorization и предупреждаем — это явный признак того,
# что список доменов не настроен.
allow_credentials = allow_origins != ["*"]
if not allow_credentials:
    logger.warning(
        "PLACE_URL не задан: CORS открыт для всех origin без credentials. "
        "Укажите список доменов фронтенда в переменной PLACE_URL."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация при старте (создание таблиц, админ). Заменяет устаревший on_event.
    await on_startup()
    yield


def create_app() -> FastAPI:
    """
    Создаёт и настраивает экземпляр FastAPI приложения.

    Возвращает:
        FastAPI: Настроенное приложение с подключёнными маршрутами и middleware.
    """
    app = FastAPI(
        title="Онлайн Платформа Обучения",
        description="Бэкенд для онлайн-платформы с логином, регистрацией и доступом к модулям",
        version="1.4.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    # Публично раздаём только аватарки. Учебные материалы и домашние работы
    # (static/lesson_docs) намеренно НЕ монтируются сюда — они доступны лишь через
    # защищённый JWT эндпоинт /files/download, иначе их можно было бы скачать в обход
    # авторизации напрямую по /static/lesson_docs/...
    os.makedirs("static/photos", exist_ok=True)
    app.mount("/static/photos", StaticFiles(directory="static/photos"), name="static-photos")

    # Заголовки безопасности на каждый ответ.
    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        # API отдаёт JSON и файлы (как attachment) — контенту нечего исполнять.
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        # HSTS только для HTTPS (в т.ч. за обратным прокси). На локальном http не шлём,
        # иначе браузер запомнит и начнёт принудительно открывать localhost по https.
        is_https = (
            request.url.scheme == "https"
            or request.headers.get("x-forwarded-proto") == "https"
        )
        if is_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Подключение роутеров
    app.include_router(login_router, prefix="/auth", tags=["Аутентификация"])
    app.include_router(access_router, prefix="/access", tags=["Доступы"])
    app.include_router(admin_modules_router, prefix="/admin/modules", tags=["Модули"])
    app.include_router(admin_user_router, prefix="/admin/users", tags=["Пользователи"])
    app.include_router(admin_groups_router, prefix="/admin/groups", tags=["Группы"])
    app.include_router(lessons_router, prefix="/lessons", tags=["Уроки"])
    app.include_router(tests_router, prefix="/tests", tags=["Тестирования"])
    app.include_router(users_router, prefix="/user", tags=["Пользователя"])
    app.include_router(files_router, prefix="/files", tags=["Файлы"])

    @app.get("/", tags=["Пример"], summary="Главная страница", description="Возвращает приветственное сообщение.")
    async def read_root():
        return {"message": "Добро пожаловать на платформу!"}

    return app

app = create_app()
