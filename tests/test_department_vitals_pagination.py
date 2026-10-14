import asyncio
import json
from urllib.parse import urlencode

from fastapi import FastAPI

from service_test_support import ServiceIntegrationTestCase
from app.core.rbac import get_current_user
from app.routes.departments import router as departments_router
from app.routes.patient_vitals import router as patient_vitals_router


class DepartmentVitalsPaginationRouteTests(ServiceIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.app = FastAPI()
        self.app.include_router(departments_router)
        self.app.include_router(patient_vitals_router)
        self.actor = self.admin
        self.app.dependency_overrides[get_current_user] = lambda: self.actor

    def request(self, path, params=None):
        async def send_request():
            messages = []
            query_string = urlencode(params or {}).encode()

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                messages.append(message)

            scope = {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": query_string,
                "root_path": "",
                "headers": [(b"host", b"testserver")],
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
            }
            await self.app(scope, receive, send)
            body = b"".join(message.get("body", b"") for message in messages)
            return messages[0]["status"], json.loads(body) if body else None

        return asyncio.run(send_request())

    def test_routes_reject_invalid_pagination_parameters(self):
        for path in ("/departments", "/patient-vitals"):
            for params in ({"skip": -1}, {"limit": 0}, {"limit": 101}):
                with self.subTest(path=path, params=params):
                    status, _ = self.request(path, params)
                    self.assertEqual(status, 422)

    def test_routes_keep_role_permissions_and_return_empty_lists(self):
        for path in ("/departments", "/patient-vitals"):
            with self.subTest(path=path, role="admin"):
                self.actor = self.admin
                status, body = self.request(path)
                self.assertEqual(status, 200)
                self.assertEqual(body, [])
            with self.subTest(path=path, role="patient"):
                self.actor = {"role": "patient", "user_id": self.admin["user_id"]}
                status, _ = self.request(path, {"skip": 0, "limit": 10})
                self.assertEqual(status, 403)
