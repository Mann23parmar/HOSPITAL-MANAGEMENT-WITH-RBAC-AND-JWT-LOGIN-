from fastapi import HTTPException

from service_test_support import ServiceIntegrationTestCase
from app.schemas.patient_vitals import PatientVitalsCreate, PatientVitalsUpdate
from app.services import patient_vitals_service as service


class PatientVitalsServiceTests(ServiceIntegrationTestCase):
    def payload(self, patient_id, nurse_id):
        return PatientVitalsCreate(patient_id=str(patient_id), nurse_id=str(nurse_id), blood_pressure="120/80", temperature=98.6, pulse_rate=72, weight=65.5)

    def test_create_list_update_and_delete_vitals(self):
        patient_id, nurse_id = self.add_patient(), self.add_nurse()
        service.create_patient_vitals(self.payload(patient_id, nurse_id), self.admin)
        saved = self.db.patient_vitals.find_one({"patient_id": patient_id})
        self.assertEqual(len(service.get_patient_vitals(self.admin)), 1)
        service.update_patient_vitals(str(saved["_id"]), PatientVitalsUpdate(weight=66.0), self.admin)
        self.assertEqual(self.db.patient_vitals.find_one({"_id": saved["_id"]})["weight"], 66.0)
        service.delete_patient_vitals(str(saved["_id"]), self.admin)
        self.assertEqual(self.db.patient_vitals.count_documents({}), 0)

    def test_nurse_sees_and_updates_only_vitals_they_recorded(self):
        first_user, second_user = self.add_user("nurse"), self.add_user("nurse")
        first_nurse, second_nurse = self.add_nurse(first_user), self.add_nurse(second_user)
        patient_id = self.add_patient()
        actor = {"user_id": str(first_user), "email": "nurse@example.test", "role": "nurse"}
        service.create_patient_vitals(self.payload(patient_id, first_nurse), actor)
        own = self.db.patient_vitals.find_one({"nurse_id": first_nurse})
        other_id = self.db.patient_vitals.insert_one({"patient_id": patient_id, "nurse_id": second_nurse, "blood_pressure": "110/70", "temperature": 98.0, "pulse_rate": 70, "weight": 60.0}).inserted_id
        self.assertEqual(len(service.get_patient_vitals(actor)), 1)
        with self.assertRaises(HTTPException) as denied:
            service.update_patient_vitals(str(other_id), PatientVitalsUpdate(weight=61.0), actor)
        self.assertEqual(denied.exception.status_code, 403)
        with self.assertRaises(HTTPException) as wrong_owner:
            service.create_patient_vitals(self.payload(patient_id, second_nurse), actor)
        self.assertEqual(wrong_owner.exception.status_code, 403)
        self.assertEqual(own["nurse_id"], first_nurse)
