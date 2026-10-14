from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from service_test_support import ServiceIntegrationTestCase
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.services import doctors_service as service


class DoctorServiceTests(ServiceIntegrationTestCase):
    def test_create_list_update_and_delete_deactivates_linked_account(self):
        user_id, department_id = self.add_user("doctor"), self.add_department()
        payload = DoctorCreate(user_id=str(user_id), department_id=str(department_id), name="Dr. New", specialization="Cardiology", phone="9876543210")
        service.create_doctor(payload, self.admin)
        saved = self.db.doctors.find_one({"user_id": user_id})
        self.assertEqual(len(service.get_doctors(self.admin)), 1)
        service.update_doctor(str(saved["_id"]), DoctorUpdate(name="Dr. Updated"), self.admin)
        self.assertEqual(self.db.doctors.find_one({"_id": saved["_id"]})["name"], "Dr. Updated")
        service.delete_doctor(str(saved["_id"]), self.admin)
        self.assertFalse(self.db.users.find_one({"_id": user_id})["is_active"])
        self.assertEqual(self.db.audit_logs.count_documents({}), 4)

    def test_duplicate_profile_wrong_role_and_referenced_delete_are_rejected(self):
        user_id, department_id = self.add_user("doctor"), self.add_department()
        doctor_id = self.add_doctor(user_id, department_id)
        with self.assertRaises(HTTPException):
            service.create_doctor(DoctorCreate(user_id=str(user_id), department_id=str(department_id), name="Other", specialization="Surgery", phone="9876543211"), self.admin)
        with self.assertRaises(HTTPException):
            service.create_doctor(DoctorCreate(user_id=str(self.add_user("nurse")), department_id=str(department_id), name="Wrong role", specialization="Surgery", phone="9876543212"), self.admin)
        self.add_appointment(doctor_id=doctor_id)
        with self.assertRaises(HTTPException) as error:
            service.delete_doctor(str(doctor_id), self.admin)
        self.assertEqual(error.exception.status_code, 409)

    def test_unique_profile_index_rejects_racing_duplicate_insert(self):
        user_id, department_id = self.add_user("doctor"), self.add_department()
        self.add_doctor(user_id, department_id)
        with self.assertRaises(DuplicateKeyError):
            self.db.doctors.insert_one({"user_id": user_id, "_unique_user_profile": True, "department_id": department_id, "name": "Duplicate", "specialization": "Surgery", "phone": "9876543213"})
