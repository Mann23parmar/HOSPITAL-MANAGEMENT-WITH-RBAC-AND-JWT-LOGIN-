from fastapi import HTTPException
from pydantic import ValidationError

from service_test_support import ServiceIntegrationTestCase
from app.schemas.user import UserCreate, UserStatusUpdate
from app.services import users_service as service


class UserServiceTests(ServiceIntegrationTestCase):
    def test_create_staff_user_normalizes_email_and_hashes_password(self):
        payload = UserCreate(email="  Nurse@Example.Test ", password="Secure!Pass1", role="nurse")
        result = service.create_user(payload, self.admin)
        saved = self.db.users.find_one({"_id": ObjectId(result["user_id"])})
        self.assertEqual(saved["email"], "nurse@example.test")
        self.assertEqual(saved["email_normalized"], "nurse@example.test")
        self.assertNotEqual(saved["password"], payload.password)
        self.assertTrue(auth_service.verify_password(payload.password, saved["password"]))
        self.assertTrue(saved["is_active"])

    def test_duplicate_email_status_rules_and_allowed_roles(self):
        service.create_user(UserCreate(email="staff@example.test", password="Secure!Pass1", role="receptionist"), self.admin)
        with self.assertRaises(HTTPException) as duplicate:
            service.create_user(UserCreate(email="STAFF@example.test", password="Secure!Pass1", role="nurse"), self.admin)
        self.assertEqual(duplicate.exception.status_code, 409)
        with self.assertRaises(ValidationError):
            UserCreate(email="admin@example.test", password="Secure!Pass1", role="admin")
        user_id = self.add_user("nurse")
        service.update_user_status(str(user_id), UserStatusUpdate(is_active=False), self.admin)
        self.assertFalse(self.db.users.find_one({"_id": user_id})["is_active"])
        with self.assertRaises(HTTPException):
            service.update_user_status(str(user_id), UserStatusUpdate(is_active=True), {**self.admin, "user_id": str(user_id)})
        admin_id = self.add_user("admin")
        with self.assertRaises(HTTPException) as protected:
            service.update_user_status(str(admin_id), UserStatusUpdate(is_active=False), self.admin)
        self.assertEqual(protected.exception.status_code, 403)


from bson import ObjectId
from app.services import auth_service
