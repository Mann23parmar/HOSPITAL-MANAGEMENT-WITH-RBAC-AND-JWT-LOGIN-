from fastapi import HTTPException

from service_test_support import ServiceIntegrationTestCase
from app.schemas.nurse import NurseCreate, NurseUpdate
from app.services import nurses_service as service


class NurseServiceTests(ServiceIntegrationTestCase):
    def test_create_list_update_and_delete_deactivates_linked_account(self):
        user_id, department_id = self.add_user("nurse"), self.add_department()
        service.create_nurse(NurseCreate(user_id=str(user_id), department_id=str(department_id), name="Nurse New", phone="9876543210"), self.admin)
        saved = self.db.nurses.find_one({"user_id": user_id})
        self.assertEqual(len(service.get_nurses(self.admin)), 1)
        service.update_nurse(str(saved["_id"]), NurseUpdate(name="Nurse Updated"), self.admin)
        self.assertEqual(self.db.nurses.find_one({"_id": saved["_id"]})["name"], "Nurse Updated")
        service.delete_nurse(str(saved["_id"]), self.admin)
        self.assertFalse(self.db.users.find_one({"_id": user_id})["is_active"])
        self.assertEqual(self.db.audit_logs.count_documents({}), 4)

    def test_duplicate_profile_wrong_role_and_vitals_reference_are_rejected(self):
        user_id, department_id = self.add_user("nurse"), self.add_department()
        nurse_id = self.add_nurse(user_id, department_id)
        with self.assertRaises(HTTPException):
            service.create_nurse(NurseCreate(user_id=str(user_id), department_id=str(department_id), name="Duplicate", phone="9876543211"), self.admin)
        with self.assertRaises(HTTPException):
            service.create_nurse(NurseCreate(user_id=str(self.add_user("doctor")), department_id=str(department_id), name="Wrong role", phone="9876543212"), self.admin)
        self.db.patient_vitals.insert_one({"patient_id": self.add_patient(), "nurse_id": nurse_id})
        with self.assertRaises(HTTPException) as error:
            service.delete_nurse(str(nurse_id), self.admin)
        self.assertEqual(error.exception.status_code, 409)
