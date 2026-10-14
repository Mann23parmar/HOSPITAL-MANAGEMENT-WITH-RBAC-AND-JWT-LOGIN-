from fastapi import HTTPException

from service_test_support import ServiceIntegrationTestCase
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordUpdate
from app.services import medical_records_service as service


class MedicalRecordServiceTests(ServiceIntegrationTestCase):
    def payload(self, patient_id, doctor_id, appointment_id):
        return MedicalRecordCreate(patient_id=str(patient_id), doctor_id=str(doctor_id), appointment_id=str(appointment_id), diagnosis="Mild hypertension", treatment="Regular monitoring", notes="Follow up in two weeks")

    def test_create_list_update_and_delete_medical_record(self):
        patient_id, doctor_id = self.add_patient(), self.add_doctor()
        appointment_id = self.add_appointment(patient_id, doctor_id)
        service.create_medical_record(self.payload(patient_id, doctor_id, appointment_id), self.admin)
        saved = self.db.medical_records.find_one({"appointment_id": appointment_id})
        self.assertEqual(len(service.get_medical_records(self.admin)), 1)
        service.update_medical_record(str(saved["_id"]), MedicalRecordUpdate(diagnosis="Updated diagnosis"), self.admin)
        self.assertEqual(self.db.medical_records.find_one({"_id": saved["_id"]})["diagnosis"], "Updated diagnosis")
        service.delete_medical_record(str(saved["_id"]), self.admin)
        self.assertEqual(self.db.medical_records.count_documents({}), 0)

    def test_appointment_patient_doctor_relationship_and_prescription_links_are_enforced(self):
        patient_id, doctor_id = self.add_patient(), self.add_doctor()
        appointment_id = self.add_appointment(patient_id, doctor_id)
        with self.assertRaises(HTTPException) as wrong_patient:
            service.create_medical_record(self.payload(self.add_patient(), doctor_id, appointment_id), self.admin)
        self.assertEqual(wrong_patient.exception.status_code, 400)
        service.create_medical_record(self.payload(patient_id, doctor_id, appointment_id), self.admin)
        record_id = self.db.medical_records.find_one({"appointment_id": appointment_id})["_id"]
        self.db.prescriptions.insert_one({"medical_record_id": record_id})
        with self.assertRaises(HTTPException) as linked:
            service.delete_medical_record(str(record_id), self.admin)
        self.assertEqual(linked.exception.status_code, 409)
        with self.assertRaises(HTTPException) as malformed:
            service.update_medical_record("bad-id", MedicalRecordUpdate(diagnosis="Updated"), self.admin)
        self.assertEqual(malformed.exception.status_code, 400)
