from datetime import date, time, timedelta

from fastapi import HTTPException

from service_test_support import ServiceIntegrationTestCase
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.services import appointments_service as service


class AppointmentServiceTests(ServiceIntegrationTestCase):
    def test_create_list_update_and_delete_appointment(self):
        patient_id, doctor_id = self.add_patient(), self.add_doctor()
        payload = AppointmentCreate(patient_id=str(patient_id), doctor_id=str(doctor_id), appointment_date=date.today() + timedelta(days=2), appointment_time=time(11, 15), reason="Regular consultation")
        service.create_appointment(payload, self.admin)
        saved = self.db.appointments.find_one({"doctor_id": doctor_id})
        self.assertEqual(len(service.get_appointments(self.admin)), 1)
        service.update_appointment(str(saved["_id"]), AppointmentUpdate(status="completed"), self.admin)
        self.assertEqual(self.db.appointments.find_one({"_id": saved["_id"]})["status"], "completed")
        service.delete_appointment(str(saved["_id"]), self.admin)
        self.assertEqual(self.db.appointments.count_documents({}), 0)

    def test_scheduling_conflicts_status_rules_and_record_link_are_enforced(self):
        patient_id, doctor_id = self.add_patient(), self.add_doctor()
        appt_id = self.add_appointment(patient_id, doctor_id)
        with self.assertRaises(HTTPException) as conflict:
            service.create_appointment(AppointmentCreate(patient_id=str(patient_id), doctor_id=str(doctor_id), appointment_date=date.today() + timedelta(days=1), appointment_time=time(10, 30), reason="Duplicate slot"), self.admin)
        self.assertEqual(conflict.exception.status_code, 409)
        with self.assertRaises(HTTPException) as invalid_status:
            service.update_appointment(str(appt_id), AppointmentUpdate(status="unknown"), self.admin)
        self.assertEqual(invalid_status.exception.status_code, 400)
        self.db.medical_records.insert_one({"appointment_id": appt_id})
        with self.assertRaises(HTTPException) as linked:
            service.delete_appointment(str(appt_id), self.admin)
        self.assertEqual(linked.exception.status_code, 409)

    def test_doctor_only_reads_and_updates_own_appointments(self):
        own_user, other_user = self.add_user("doctor"), self.add_user("doctor")
        own_doctor, other_doctor = self.add_doctor(own_user), self.add_doctor(other_user)
        own_id = self.add_appointment(doctor_id=own_doctor)
        self.add_appointment(doctor_id=other_doctor, when="11:30:00")
        actor = {"user_id": str(own_user), "email": "own@example.test", "role": "doctor"}
        self.assertEqual(len(service.get_appointments(actor)), 1)
        with self.assertRaises(HTTPException) as denied:
            service.update_appointment(str(self.db.appointments.find_one({"doctor_id": other_doctor})["_id"]), AppointmentUpdate(reason="Changed reason"), actor)
        self.assertEqual(denied.exception.status_code, 403)
