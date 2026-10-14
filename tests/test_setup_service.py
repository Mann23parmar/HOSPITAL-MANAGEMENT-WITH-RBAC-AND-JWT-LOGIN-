import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pydantic import ValidationError

from service_test_support import ServiceIntegrationTestCase
from app.schemas.setup import InitialAdminCreate
from app.services import setup_service as service


class SetupServiceTests(ServiceIntegrationTestCase):
    def invitation(self, token, email, expires_at=None):
        self.db.admin_invitations.insert_one({"token_hash": hashlib.sha256(token.encode()).hexdigest(), "email": email, "used": False, "active_invitation": True, "expires_at": expires_at or datetime.now(timezone.utc) + timedelta(minutes=10)})

    def test_valid_invitation_creates_single_admin_and_consumes_token(self):
        token, email = "invitation-token-value-123456", "first.admin@example.test"
        self.invitation(token, email)
        result = service.create_initial_admin(InitialAdminCreate(email=email, password="Secure!Pass1", invitation_token=token))
        self.assertEqual(result["message"], "Initial admin created successfully")
        self.assertEqual(self.db.users.count_documents({"role": "admin"}), 1)
        invite = self.db.admin_invitations.find_one({"token_hash": hashlib.sha256(token.encode()).hexdigest()})
        self.assertTrue(invite["used"])
        with self.assertRaises(HTTPException):
            service.create_initial_admin(InitialAdminCreate(email=email, password="Secure!Pass1", invitation_token=token))

    def test_expired_mismatched_or_used_invitation_cannot_create_admin(self):
        token, email = "expired-invitation-token-12345", "admin@example.test"
        self.invitation(token, email, datetime.now(timezone.utc) - timedelta(seconds=1))
        with self.assertRaises(HTTPException) as error:
            service.create_initial_admin(InitialAdminCreate(email=email, password="Secure!Pass1", invitation_token=token))
        self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(self.db.users.count_documents({}), 0)
        self.assertEqual(self.db.admin_invitations.find_one({"email": email})["used"], False)
