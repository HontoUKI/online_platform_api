from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.startup import on_startup

from app.api.endpoints.login import router as login_router
from app.api.admin_endpoints.users import router as admin_user_router
from app.api.admin_endpoints.groups import router as admin_groups_router
from app.api.admin_endpoints.modules import router as admin_modules_router
from app.api.endpoints.lessons import router as lessons_router
from app.api.endpoints.tests import router as tests_router
from app.api.endpoints.access import router as access_router
from app.api.endpoints.user import router as users_router


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
    )
     
    #Старт
    @app.on_event("startup")
    async def startup_event():
        for route in app.routes:
            print(route.path)

        await on_startup()

    # Раздача папки static
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
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


    # Пример базового эндпоинта
    @app.get("/", tags=["Пример"], summary="Главная страница", description="Возвращает приветственное сообщение.")
    async def read_root():
        return {"message": "Добро пожаловать на платформу!"}


    return app

app = create_app()
