"""MongoDB integration checks for prescription and stock services.

Run with ``python -m unittest discover -s tests`` against a disposable MongoDB.
The tests use a temporary database and real concurrent MongoDB updates.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from threading import Barrier
from unittest import TestCase, mock
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException
from pymongo import MongoClient

from app.core.config import settings
from app.routes.prescriptions import router
from app.schemas.prescription import PrescriptionCreate, PrescriptionUpdate
from app.services import prescription_service as workflow
from app.services import prescription_stock_service as stock
from app.services import audit_service


class PrescriptionServiceIntegrationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=2000)
        cls.client.admin.command("ping")
        cls.db = cls.client[f"hospital_prescription_test_{uuid4().hex}"]
        cls.collections = {
            "prescriptions_collection": cls.db.prescriptions,
            "patients_collection": cls.db.patients,
            "doctors_collection": cls.db.doctors,
            "medical_records_collection": cls.db.medical_records,
            "medicines_collection": cls.db.medicines,
        }
        cls.originals = {}
        for module in (workflow, stock):
            for name, collection in cls.collections.items():
                if hasattr(module, name):
                    cls.originals[(module, name)] = getattr(module, name)
                    setattr(module, name, collection)
        cls.original_audit_collection = audit_service.audit_logs_collection
        audit_service.audit_logs_collection = cls.db.audit_logs

    @classmethod
    def tearDownClass(cls):
        cls.client.drop_database(cls.db.name)
        for (module, name), collection in cls.originals.items():
            setattr(module, name, collection)
        audit_service.audit_logs_collection = cls.original_audit_collection
        cls.client.close()

    def setUp(self):
        for collection in self.collections.values():
            collection.delete_many({})
        self.db.audit_logs.delete_many({})
        self.patient_id, self.doctor_id = ObjectId(), ObjectId()
        self.record_id = ObjectId()
        self.db.patients.insert_one({"_id": self.patient_id, "name": "Patient"})
        self.db.doctors.insert_one({"_id": self.doctor_id, "name": "Doctor"})
        self.db.medical_records.insert_one(
            {
                "_id": self.record_id,
                "patient_id": self.patient_id,
                "doctor_id": self.doctor_id,
            }
        )
        self.admin = {"role": "admin", "email": "admin@example.test"}

    def medicine(self, quantity):
        medicine_id = ObjectId()
        self.db.medicines.insert_one(
            {
                "_id": medicine_id,
                "name": "Medicine",
                "quantity": quantity,
                "expiry_date": (date.today() + timedelta(days=1)).isoformat(),
            }
        )
        return medicine_id

    def payload(self, medicine_id, quantity=2):
        return PrescriptionCreate(
            patient_id=str(self.patient_id),
            doctor_id=str(self.doctor_id),
            medical_record_id=str(self.record_id),
            medicine_id=str(medicine_id),
            quantity=quantity,
            dosage="10 mg",
            frequency="Daily",
            duration="5 days",
            instructions="After food",
        )

    def test_create_retrieve_update_swap_and_delete_keep_stock_consistent(self):
        first_id, second_id = self.medicine(8), self.medicine(10)
        workflow.create_prescription(self.payload(first_id), self.admin)
        first = self.db.medicines.find_one({"_id": first_id})
        self.assertEqual(first["quantity"], 6)
        saved = self.db.prescriptions.find_one({})
        result = workflow.get_prescriptions(self.admin)
        self.assertEqual(len(result), 1)

        workflow.update_prescription(
            str(saved["_id"]),
            PrescriptionUpdate(dosage="20 mg"),
            self.admin,
        )
        self.assertEqual(self.db.medicines.find_one({"_id": first_id})["quantity"], 6)

        workflow.update_prescription(
            str(saved["_id"]),
            PrescriptionUpdate(medicine_id=str(second_id)),
            self.admin,
        )
        self.assertEqual(self.db.medicines.find_one({"_id": first_id})["quantity"], 8)
        self.assertEqual(self.db.medicines.find_one({"_id": second_id})["quantity"], 8)
        workflow.delete_prescription(str(saved["_id"]), self.admin)
        self.assertEqual(self.db.medicines.find_one({"_id": second_id})["quantity"], 10)
        self.assertEqual(self.db.prescriptions.count_documents({}), 0)
        self.assertEqual(self.db.audit_logs.count_documents({}), 5)

    def test_insufficient_stock_is_rejected_without_writing_prescription(self):
        medicine_id = self.medicine(1)
        with self.assertRaises(HTTPException) as error:
            workflow.create_prescription(self.payload(medicine_id, 2), self.admin)
        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(
            self.db.medicines.find_one({"_id": medicine_id})["quantity"], 1
        )
        self.assertEqual(self.db.prescriptions.count_documents({}), 0)

    def test_invalid_patient_reference_is_rejected(self):
        medicine_id = self.medicine(3)
        payload = self.payload(medicine_id)
        payload.patient_id = str(ObjectId())
        with self.assertRaises(HTTPException) as error:
            workflow.create_prescription(payload, self.admin)
        self.assertEqual(error.exception.status_code, 404)

    def test_ambiguous_insert_ack_does_not_refund_committed_prescription(self):
        medicine_id = self.medicine(5)
        insert_one = workflow.prescriptions_collection.insert_one

        def insert_then_raise(document, *args, **kwargs):
            insert_one(document, *args, **kwargs)
            raise RuntimeError("write acknowledgment lost")

        with mock.patch.object(
            workflow.prescriptions_collection,
            "insert_one",
            side_effect=insert_then_raise,
        ):
            with self.assertRaises(RuntimeError):
                workflow.create_prescription(self.payload(medicine_id), self.admin)
        self.assertEqual(
            self.db.medicines.find_one({"_id": medicine_id})["quantity"], 3
        )
        saved = self.db.prescriptions.find_one({})
        self.assertIsNotNone(saved)
        self.assertNotIn("stock_reservation_id", saved)

    def test_stock_reservations_are_atomic_under_real_concurrency(self):
        medicine_id = self.medicine(5)

        def reserve(_):
            try:
                stock.reserve_medicine_stock(medicine_id, 1)
                return True
            except HTTPException:
                return False

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(reserve, range(10)))
        self.assertEqual(sum(results), 5)
        self.assertEqual(
            self.db.medicines.find_one({"_id": medicine_id})["quantity"], 0
        )

    def test_concurrent_prescription_creates_never_oversell_stock(self):
        medicine_id = self.medicine(5)

        def create(_):
            try:
                workflow.create_prescription(self.payload(medicine_id, 1), self.admin)
                return True
            except HTTPException as error:
                if error.status_code == 400:
                    return False
                raise

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(create, range(10)))

        self.assertEqual(sum(results), 5)
        self.assertEqual(self.db.prescriptions.count_documents({}), 5)
        self.assertEqual(
            self.db.medicines.find_one({"_id": medicine_id})["quantity"], 0
        )

    def test_startup_recovery_completes_an_expired_interrupted_swap(self):
        previous_id, target_id, prescription_id = ObjectId(), ObjectId(), ObjectId()
        self.db.medicines.insert_many(
            [
                {"_id": previous_id, "quantity": 0},
                {
                    "_id": target_id,
                    "quantity": 8,
                    "_prescription_reservation_leases": [
                        {
                            "lease_id": "startup-swap",
                            "quantity": 2,
                            "expires_at": datetime.now(timezone.utc)
                            - timedelta(seconds=1),
                        }
                    ],
                },
            ]
        )
        self.db.prescriptions.insert_one(
            {
                "_id": prescription_id,
                "medicine_id": target_id,
                "stock_transition": {
                    "reservation_id": "startup-swap",
                    "previous_medicine_id": previous_id,
                    "target_medicine_id": target_id,
                    "quantity": 2,
                    "expires_at": datetime.now(timezone.utc) - timedelta(seconds=1),
                },
            }
        )

        from app.main import recover_abandoned_stock_reservations

        recover_abandoned_stock_reservations()

        self.assertEqual(
            self.db.medicines.find_one({"_id": previous_id})["quantity"], 2
        )
        self.assertEqual(
            self.db.medicines.find_one({"_id": target_id})["quantity"], 8
        )
        self.assertNotIn(
            "stock_transition", self.db.prescriptions.find_one({"_id": prescription_id})
        )

    def test_startup_recovery_error_propagates_and_prevents_startup(self):
        from app import main

        with mock.patch.object(
            main,
            "reconcile_expired_stock_reservations",
            side_effect=RuntimeError("MongoDB recovery failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "MongoDB recovery failed"):
                main.recover_abandoned_stock_reservations()

    def test_interrupted_swap_before_prescription_update_refunds_target_stock(self):
        previous_id, target_id, prescription_id = ObjectId(), ObjectId(), ObjectId()
        self.db.medicines.insert_many(
            [
                {"_id": previous_id, "quantity": 3},
                {
                    "_id": target_id,
                    "quantity": 6,
                    "_prescription_reservation_leases": [
                        {"lease_id": "rollback-swap", "quantity": 2}
                    ],
                },
            ]
        )
        self.db.prescriptions.insert_one(
            {
                "_id": prescription_id,
                "medicine_id": previous_id,
                "stock_transition": {
                    "reservation_id": "rollback-swap",
                    "previous_medicine_id": previous_id,
                    "target_medicine_id": target_id,
                    "quantity": 2,
                },
            }
        )

        stock.recover_stock_transition("rollback-swap")

        self.assertEqual(
            self.db.medicines.find_one({"_id": previous_id})["quantity"], 3
        )
        self.assertEqual(
            self.db.medicines.find_one({"_id": target_id})["quantity"], 8
        )
        self.assertNotIn(
            "stock_transition", self.db.prescriptions.find_one({"_id": prescription_id})
        )

    def test_recovery_can_retry_after_database_error_without_double_restore(self):
        previous_id, target_id, prescription_id = ObjectId(), ObjectId(), ObjectId()
        self.db.medicines.insert_many(
            [
                {"_id": previous_id, "quantity": 0},
                {"_id": target_id, "quantity": 8},
            ]
        )
        reservation_id = str(uuid4())
        self.db.prescriptions.insert_one(
            {
                "_id": prescription_id,
                "medicine_id": target_id,
                "stock_transition": {
                    "reservation_id": reservation_id,
                    "previous_medicine_id": previous_id,
                    "target_medicine_id": target_id,
                    "quantity": 2,
                },
            }
        )
        update = stock.medicines_collection.update_one
        failed = False

        def apply_then_fail_once(query, changes, *args, **kwargs):
            nonlocal failed
            if query.get("_id") == previous_id and not failed:
                failed = True
                update(query, changes, *args, **kwargs)
                raise RuntimeError("temporary database failure")
            return update(query, changes, *args, **kwargs)

        with mock.patch.object(
            stock.medicines_collection, "update_one", side_effect=apply_then_fail_once
        ):
            with self.assertRaises(RuntimeError):
                stock.recover_stock_transition(reservation_id)
        stock.recover_stock_transition(reservation_id)
        stock.recover_stock_transition(reservation_id)
        self.assertEqual(
            self.db.medicines.find_one({"_id": previous_id})["quantity"], 2
        )
        self.assertNotIn(
            "stock_transition", self.db.prescriptions.find_one({"_id": prescription_id})
        )

    def test_interrupted_delete_retry_does_not_restore_stock_twice(self):
        medicine_id, prescription_id = ObjectId(), ObjectId()
        reservation_id = str(uuid4())
        self.db.medicines.insert_one({"_id": medicine_id, "quantity": 0})
        self.db.prescriptions.insert_one(
            {
                "_id": prescription_id,
                "medicine_id": medicine_id,
                "stock_transition": {
                    "action": "delete",
                    "reservation_id": reservation_id,
                    "previous_medicine_id": medicine_id,
                    "quantity": 3,
                },
            }
        )
        delete_one = stock.prescriptions_collection.delete_one
        failed = False

        def fail_delete_once(query, *args, **kwargs):
            nonlocal failed
            if not failed:
                failed = True
                raise RuntimeError("temporary delete failure")
            return delete_one(query, *args, **kwargs)

        with mock.patch.object(
            stock.prescriptions_collection,
            "delete_one",
            side_effect=fail_delete_once,
        ):
            with self.assertRaisesRegex(RuntimeError, "temporary delete failure"):
                stock.recover_stock_transition(reservation_id)
            stock.recover_stock_transition(reservation_id)
        self.assertEqual(
            self.db.medicines.find_one({"_id": medicine_id})["quantity"], 3
        )
        self.assertEqual(self.db.prescriptions.count_documents({}), 0)

    def test_parallel_recovery_workers_process_a_transition_once(self):
        previous_id, target_id, prescription_id = ObjectId(), ObjectId(), ObjectId()
        self.db.medicines.insert_many(
            [
                {"_id": previous_id, "quantity": 0},
                {
                    "_id": target_id,
                    "quantity": 8,
                    "_prescription_reservation_leases": [
                        {
                            "lease_id": "swap-once",
                            "quantity": 2,
                            "expires_at": datetime.now(timezone.utc)
                            - timedelta(seconds=1),
                        }
                    ],
                },
            ]
        )
        self.db.prescriptions.insert_one(
            {
                "_id": prescription_id,
                "medicine_id": target_id,
                "stock_transition": {
                    "reservation_id": "swap-once",
                    "previous_medicine_id": previous_id,
                    "target_medicine_id": target_id,
                    "quantity": 2,
                    "expires_at": datetime.now(timezone.utc) - timedelta(seconds=1),
                },
            }
        )
        original_find_one = stock.prescriptions_collection.find_one
        readers_at_transition = Barrier(4)

        def synchronized_find_one(query, *args, **kwargs):
            if query.get("stock_transition.reservation_id") == "swap-once":
                readers_at_transition.wait(timeout=5)
            return original_find_one(query, *args, **kwargs)

        with mock.patch.object(
            stock.prescriptions_collection,
            "find_one",
            side_effect=synchronized_find_one,
        ):
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda _: stock.recover_stock_transition("swap-once"), range(4)))
        self.assertEqual(
            self.db.medicines.find_one({"_id": previous_id})["quantity"], 2
        )
        self.assertNotIn(
            "stock_transition", self.db.prescriptions.find_one({"_id": prescription_id})
        )

    def test_router_still_exposes_all_existing_endpoints(self):
        routes = {(route.path, tuple(route.methods)) for route in router.routes}
        self.assertIn(("/prescriptions", ("POST",)), routes)
        self.assertIn(("/prescriptions", ("GET",)), routes)
        self.assertIn(("/prescriptions/{prescription_id}", ("PUT",)), routes)
        self.assertIn(("/prescriptions/{prescription_id}", ("DELETE",)), routes)
    
        
        






