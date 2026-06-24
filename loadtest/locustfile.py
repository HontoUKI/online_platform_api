"""Нагрузочный сценарий (Locust) для Online Platform API.

Сценарий: каждый виртуальный пользователь один раз логинится (получает JWT),
затем циклически выполняет авторизованные GET-запросы — имитация «просмотра»
платформы. По умолчанию только чтение, чтобы не засорять БД.

Запуск (см. README → Load testing):
    locust -f loadtest/locustfile.py --host http://localhost:8000
Заголовочные креды берутся из окружения LOAD_TEST_IIN / LOAD_TEST_PASSWORD.
"""
import os

from locust import HttpUser, task, between

IIN = os.getenv("LOAD_TEST_IIN", "000000000000")
PASSWORD = os.getenv("LOAD_TEST_PASSWORD", "")


class PlatformUser(HttpUser):
    # Пауза между запросами одного пользователя — имитация «думающего» человека.
    wait_time = between(1, 3)

    def on_start(self):
        """Логинимся один раз и сохраняем заголовок авторизации."""
        self.headers = {}
        resp = self.client.post(
            "/auth/login",
            json={"iin": IIN, "password": PASSWORD},
            name="POST /auth/login",
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            # Без токена авторизованные задачи бессмысленны — останавливаем пользователя.
            resp.failure(f"login failed: {resp.status_code}")
            self.environment.runner.quit()

    @task
    def root(self):
        self.client.get("/", name="GET /")

    @task(3)
    def check_auth(self):
        self.client.get("/auth/check", headers=self.headers, name="GET /auth/check")

    @task(5)
    def my_modules(self):
        self.client.get(
            "/access/my-modules", headers=self.headers, name="GET /access/my-modules"
        )

    @task(4)
    def my_grades(self):
        self.client.get(
            "/lessons/student/grades",
            headers=self.headers,
            name="GET /lessons/student/grades",
        )
