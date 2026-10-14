from datetime import date, timedelta
from unittest import TestCase
from uuid import uuid4

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings
from app.database.index_migration import migrate_indexes

from app.core import authorization
from app.services import (
    appointments_service,
    audit_service,
    auth_service,
    departments_service,
    doctors_service,
    medical_records_service,
    medicines_service,
    nurses_service,
    patient_vitals_service,
    patients_service,
    setup_service,
    users_service,
)


SERVICE_MODULES = (
    authorization,
    appointments_service,
    departments_service,
    doctors_service,
    medical_records_service,
    medicines_service,
    nurses_service,
    patient_vitals_service,
    patients_service,
    setup_service,
    users_service,
    auth_service,
)
COLLECTION_NAMES = (
    "users", "departments", "doctors", "nurses", "patients", "appointments",
    "medical_records", "prescriptions", "medicines", "patient_vitals",
    "audit_logs", "revoked_tokens", "admin_invitations",
)


class ServiceIntegrationTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=2000)
        cls.client.admin.command("ping")
        cls.db = cls.client[f"hospital_service_test_{uuid4().hex}"]
        migrate_indexes(cls.db, output=lambda _message: None)
        cls.originals = []
        for module in SERVICE_MODULES:
            for name in COLLECTION_NAMES:
                if hasattr(module, f"{name}_collection"):
                    attr = f"{name}_collection"
                    cls.originals.append((module, attr, getattr(module, attr)))
                    setattr(module, attr, cls.db[name])
        cls.original_audit = audit_service.audit_logs_collection
        audit_service.audit_logs_collection = cls.db.audit_logs

    @classmethod
    def tearDownClass(cls):
        cls.client.drop_database(cls.db.name)
        for module, attr, original in cls.originals:
            setattr(module, attr, original)
        audit_service.audit_logs_collection = cls.original_audit
        cls.client.close()
        super().tearDownClass()

    def setUp(self):
        for name in COLLECTION_NAMES:
            self.db[name].delete_many({})
        self.admin = {"user_id": str(ObjectId()), "email": "admin@example.test", "role": "admin"}

    def add_user(self, role="doctor", email=None, active=True):
        user_id = ObjectId()
        email = email or f"{role}-{uuid4().hex[:8]}@example.test"
        self.db.users.insert_one({"_id": user_id, "email": email, "email_normalized": email.lower(), "role": role, "password": auth_service.hash_password("Password1"), "is_active": active})
        return user_id

    def add_department(self, name=None):
        department_id = ObjectId()
        self.db.departments.insert_one({"_id": department_id, "name": name or f"Dept-{uuid4().hex[:6]}", "location": "2nd Floor", "description": "General care department"})
        return department_id

    def add_patient(self, phone=None):
        patient_id = ObjectId()
        birth = date(1990, 1, 1)
        self.db.patients.insert_one({"_id": patient_id, "name": "Patient One", "age": date.today().year - birth.year - ((date.today().month, date.today().day) < (birth.month, birth.day)), "gender": "Female", "phone": phone or f"9{uuid4().int % 10**9:09d}", "address": "Ahmedabad, Gujarat", "date_of_birth": birth.isoformat(), "created_by": ObjectId(self.admin["user_id"])})
        return patient_id

    def add_doctor(self, user_id=None, department_id=None):
        doctor_id = ObjectId()
        user_id = user_id or self.add_user("doctor")
        department_id = department_id or self.add_department()
        self.db.doctors.insert_one({"_id": doctor_id, "user_id": user_id, "_unique_user_profile": True, "department_id": department_id, "name": "Doctor One", "specialization": "Cardiology", "phone": f"8{uuid4().int % 10**9:09d}"})
        return doctor_id

    def add_nurse(self, user_id=None, department_id=None):
        nurse_id = ObjectId()
        user_id = user_id or self.add_user("nurse")
        department_id = department_id or self.add_department()
        self.db.nurses.insert_one({"_id": nurse_id, "user_id": user_id, "department_id": department_id, "name": "Nurse One", "phone": f"7{uuid4().int % 10**9:09d}"})
        return nurse_id

    def add_appointment(self, patient_id=None, doctor_id=None, when=None):
        appointment_id = ObjectId()
        self.db.appointments.insert_one({"_id": appointment_id, "patient_id": patient_id or self.add_patient(), "doctor_id": doctor_id or self.add_doctor(), "created_by": ObjectId(self.admin["user_id"]), "appointment_date": (date.today() + timedelta(days=1)).isoformat(), "appointment_time": when or "10:30:00", "reason": "Regular consultation", "status": "scheduled"})
        return appointment_id

    def add_medicine(self, name=None, manufacturer=None, quantity=10):
        medicine_id = ObjectId()
        self.db.medicines.insert_one({"_id": medicine_id, "name": name or f"Med-{uuid4().hex[:6]}", "manufacturer": manufacturer or "ABC Pharma", "description": "Pain relief medication", "price": 20.0, "quantity": quantity, "expiry_date": (date.today() + timedelta(days=30)).isoformat()})
        return medicine_id
