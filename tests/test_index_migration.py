import os
from pathlib import Path
import subprocess
import sys
from unittest import TestCase, mock
from uuid import uuid4

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings
from app.database.index_migration import (
    DuplicateIndexDataError,
    IndexMigrationError,
    INDEX_DEFINITIONS,
    migrate_indexes,
)


class IndexMigrationIntegrationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=2000)
        cls.client.admin.command("ping")

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def setUp(self):
        self.database_name = f"hospital_index_migration_test_{uuid4().hex}"
        self.db = self.client[self.database_name]

    def tearDown(self):
        self.client.drop_database(self.database_name)

    def test_database_connection_import_does_not_create_indexes(self):
        project_root = Path(__file__).resolve().parents[1]
        script = (
            "from pymongo.collection import Collection\n"
            "def forbidden(*args, **kwargs):\n"
            "    raise AssertionError('index creation during import')\n"
            "Collection.create_index = forbidden\n"
            "import app.database.connection\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def run_migration_command(self):
        project_root = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment["MONGO_URL"] = settings.MONGO_URL
        environment["DATABASE_NAME"] = self.database_name
        return subprocess.run(
            [sys.executable, "-m", "scripts.migrate_indexes"],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_migration_command_creates_indexes_in_selected_database(self):
        result = self.run_migration_command()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Index migration succeeded", result.stdout)
        self.assertIn("unique_patient_phone", self.db.patients.index_information())

    def test_migration_command_returns_nonzero_for_duplicate_data(self):
        self.db.patients.insert_many([{"phone": "5550000000"}, {"phone": "5550000000"}])
        result = self.run_migration_command()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Duplicate data prevents", result.stderr)
        self.assertNotIn("unique_patient_phone", self.db.patients.index_information())

    def assert_duplicate_blocks_index_creation(self, collection, docs, index_name):
        self.db[collection].insert_many(docs)
        with self.assertRaises(DuplicateIndexDataError) as raised:
            migrate_indexes(self.db, output=lambda _message: None)
        message = str(raised.exception)
        self.assertIn(f"collection={collection}", message)
        self.assertIn(f"index={index_name}", message)
        self.assertTrue(all(index["name"] == "_id_" for name in self.db.list_collection_names() if not name.startswith("_idxcheck_") for index in self.db[name].list_indexes()))
        return message

    def test_duplicate_patient_phone_and_missing_null_keys_are_reported(self):
        first, second = uuid4().hex, uuid4().hex
        message = self.assert_duplicate_blocks_index_creation(
            "patients",
            [{"_id": first, "phone": None}, {"_id": second}],
            "unique_patient_phone",
        )
        self.assertIn(first, message)
        self.assertIn(second, message)

    def test_duplicate_medicine_compound_key_is_reported(self):
        first, second = uuid4().hex, uuid4().hex
        self.assert_duplicate_blocks_index_creation(
            "medicines",
            [
                {"_id": first, "name": "Medicine", "manufacturer": "Maker"},
                {"_id": second, "name": "Medicine", "manufacturer": "Maker"},
            ],
            "unique_medicine_manufacturer",
        )

    def test_duplicate_normalized_email_is_reported(self):
        self.assert_duplicate_blocks_index_creation(
            "users",
            [
                {"email_normalized": "same@example.test"},
                {"email_normalized": "same@example.test"},
            ],
            "unique_normalized_user_email",
        )

    def test_duplicate_scheduled_doctor_slot_is_reported(self):
        doctor_id = ObjectId()
        self.assert_duplicate_blocks_index_creation(
            "appointments",
            [
                {"doctor_id": doctor_id, "appointment_date": "2026-11-01", "appointment_time": "10:00", "status": "scheduled"},
                {"doctor_id": doctor_id, "appointment_date": "2026-11-01", "appointment_time": "10:00", "status": "scheduled"},
            ],
            "unique_scheduled_doctor_slot",
        )

    def test_partial_sparse_and_missing_field_exclusions_match_mongodb(self):
        self.db.users.insert_many([
            {"role": "doctor"},
            {"role": "doctor", "email_normalized": None},
            {"role": "nurse", "email_normalized": None},
        ])
        self.db.doctors.insert_many([
            {"user_id": "legacy-user", "_unique_user_profile": False},
            {"user_id": "legacy-user", "_unique_user_profile": False},
        ])
        self.db.departments.insert_many([{"name": None}, {}, {"name": 23}])
        self.db.appointments.insert_many([
            {"doctor_id": "legacy", "appointment_date": "day", "appointment_time": "time", "status": "cancelled"},
            {"doctor_id": "legacy", "appointment_date": "day", "appointment_time": "time", "status": "cancelled"},
        ])
        self.db.prescriptions.insert_many([{}, {}])

        result = migrate_indexes(self.db, output=lambda _message: None)

        self.assertEqual(len(result["created"]), len(INDEX_DEFINITIONS))
        self.assertEqual(self.db.prescriptions.index_information()["unique_stock_reservation_id"]["sparse"], True)
        self.assertEqual(self.db.users.index_information()["unique_normalized_user_email"]["partialFilterExpression"], {"email_normalized": {"$type": "string"}})

    def test_sparse_unique_index_includes_explicit_null_but_omits_missing(self):
        self.db.prescriptions.insert_many([{}, {"stock_reservation_id": None}, {"stock_reservation_id": None}])
        with self.assertRaises(DuplicateIndexDataError):
            migrate_indexes(self.db, output=lambda _message: None)

    def test_successful_migration_is_idempotent_and_preserves_ttl_indexes(self):
        first = migrate_indexes(self.db, output=lambda _message: None)
        before = {
            name: list(self.db[name].list_indexes())
            for name in {spec.collection for spec in INDEX_DEFINITIONS}
        }
        second = migrate_indexes(self.db, output=lambda _message: None)
        self.assertEqual(len(first["created"]), len(INDEX_DEFINITIONS))
        self.assertEqual(len(second["created"]), 0)
        self.assertEqual(len(second["skipped"]), len(INDEX_DEFINITIONS))
        after = {
            name: list(self.db[name].list_indexes())
            for name in before
        }
        self.assertEqual(before, after)
        self.assertEqual(self.db.admin_invitations.index_information()["expires_at_1"]["expireAfterSeconds"], 0)
        self.assertEqual(self.db.revoked_tokens.index_information()["expires_at_1"]["expireAfterSeconds"], 0)

    def test_conflicting_existing_index_definition_stops_migration(self):
        self.db.users.create_index("role", unique=True, name="role_1")
        with self.assertRaisesRegex(IndexMigrationError, "conflicts with existing index"):
            migrate_indexes(self.db, output=lambda _message: None)
        self.assertNotIn("unique_patient_phone", self.db.patients.index_information())

    def test_index_creation_failure_is_reported_not_claimed_as_success(self):
        with mock.patch(
            "app.database.index_migration._create_real_index",
            side_effect=RuntimeError("simulated index build failure"),
        ):
            with self.assertRaisesRegex(IndexMigrationError, "simulated index build failure"):
                migrate_indexes(self.db, output=lambda _message: None)
