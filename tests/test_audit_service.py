from datetime import datetime, timezone
from unittest import mock

from service_test_support import ServiceIntegrationTestCase
from app.services import audit_service as service


class AuditServiceTests(ServiceIntegrationTestCase):
    def test_audit_message_and_record_include_actor_action_and_timestamp(self):
        message = service.format_audit_message("Sam", "admin", "CREATE", "patient_vitals", datetime(2026, 1, 2, tzinfo=timezone.utc))
        self.assertIn("Sam (Admin) created Patient Vitals", message)
        service.create_audit_log("UPDATE", "patients", "patient-id", self.admin)
        record = self.db.audit_logs.find_one({"record_id": "patient-id"})
        self.assertEqual(record["who"], "admin@example.test")
        self.assertEqual(record["role"], "admin")

    def test_audit_database_failure_is_logged_without_escaping(self):
        with mock.patch.object(service.audit_logs_collection, "insert_one", side_effect=RuntimeError("audit offline")):
            with self.assertLogs(service.logger, level="ERROR"):
                service.create_audit_log("CREATE", "patients", "patient-id", self.admin)
