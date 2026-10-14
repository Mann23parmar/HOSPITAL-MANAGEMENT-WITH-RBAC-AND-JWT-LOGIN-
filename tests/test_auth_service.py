from fastapi import HTTPException

from service_test_support import ServiceIntegrationTestCase
from app.schemas.user import UserLogin
from app.services import auth_service as service


class AuthServiceTests(ServiceIntegrationTestCase):
    def test_login_token_validation_and_logout_revocation(self):
        user_id = self.add_user("doctor", "doctor@example.test")
        result = service.login_user(UserLogin(email=" DOCTOR@example.test ", password="Password1"))
        self.assertEqual(result["token_type"], "bearer")
        payload = service.jwt.decode(result["access_token"], service.JWT_SECRET_KEY, algorithms=[service.JWT_ALGORITHM], issuer=service.JWT_ISSUER, audience=service.JWT_AUDIENCE)
        current = service.get_current_user(type("Credentials", (), {"credentials": result["access_token"]})())
        self.assertEqual(current["user_id"], str(user_id))
        service.logout_user(current)
        with self.assertRaises(HTTPException) as revoked:
            service.get_current_user(type("Credentials", (), {"credentials": result["access_token"]})())
        self.assertEqual(revoked.exception.status_code, 401)
        self.assertEqual(self.db.revoked_tokens.count_documents({"jti": payload["jti"]}), 1)

    def test_login_rejects_bad_password_and_inactive_account(self):
        self.add_user("nurse", "nurse@example.test")
        with self.assertRaises(HTTPException) as bad_password:
            service.login_user(UserLogin(email="nurse@example.test", password="Wrong!Pass"))
        self.assertEqual(bad_password.exception.status_code, 401)
        self.db.users.update_one({"email": "nurse@example.test"}, {"$set": {"is_active": False}})
        with self.assertRaises(HTTPException) as inactive:
            service.login_user(UserLogin(email="nurse@example.test", password="Password1"))
        self.assertEqual(inactive.exception.status_code, 403)
