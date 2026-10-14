from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError

from service_test_support import ServiceIntegrationTestCase
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services import patients_service as service


class PatientServiceTests(ServiceIntegrationTestCase):
    def payload(self, phone="9876543210"):
        birth = date(1990, 1, 1)
        age = date.today().year - birth.year - ((date.today().month, date.today().day) < (birth.month, birth.day))
        return PatientCreate(name="New Patient", age=age, gender="Female", phone=phone, address="Ahmedabad, Gujarat", date_of_birth=birth)

    def test_create_retrieve_update_and_delete_patient(self):
        self.assertEqual(service.create_patient(self.payload(), self.admin)["message"], "Patient created successfully")
        saved = self.db.patients.find_one({"phone": "9876543210"})
        self.assertEqual(len(service.get_patients(self.admin)), 1)
        service.update_patient(str(saved["_id"]), PatientUpdate(name="Updated Patient"), self.admin)
        self.assertEqual(self.db.patients.find_one({"_id": saved["_id"]})["name"], "Updated Patient")
        service.delete_patient(str(saved["_id"]), self.admin)
        self.assertEqual(self.db.patients.count_documents({}), 0)
        self.assertEqual(self.db.audit_logs.count_documents({}), 3)

    def test_patient_age_phone_and_references_are_validated(self):
        with self.assertRaises(ValidationError):
            PatientCreate(name="Patient", age=20, gender="F", phone="123", address="Somewhere", date_of_birth=date(1990, 1, 1))
        patient_id = self.add_patient(phone="9876543210")
        with self.assertRaises(HTTPException) as duplicate:
            service.create_patient(self.payload(), self.admin)
        self.assertIn(duplicate.exception.status_code, (400, 409))
        existing_age = self.db.patients.find_one({"_id": patient_id})["age"]
        with self.assertRaises(HTTPException) as inconsistent_update:
            service.update_patient(str(patient_id), PatientUpdate(age=existing_age + 1), self.admin)
        self.assertEqual(inconsistent_update.exception.status_code, 400)
        with self.assertRaises(HTTPException) as malformed:
            service.update_patient("bad-id", PatientUpdate(name="Updated"), self.admin)
        self.assertEqual(malformed.exception.status_code, 400)
        doctor_id = self.add_doctor()
        self.add_appointment(patient_id=patient_id, doctor_id=doctor_id)
        with self.assertRaises(HTTPException) as linked:
            service.delete_patient(str(patient_id), self.admin)
        self.assertEqual(linked.exception.status_code, 409)
