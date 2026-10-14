from datetime import date, timedelta

from fastapi import HTTPException
from pydantic import ValidationError

from service_test_support import ServiceIntegrationTestCase
from app.schemas.medicine import MedicineCreate, MedicineUpdate
from app.services import medicines_service as service


class MedicineServiceTests(ServiceIntegrationTestCase):
    def payload(self, name="Paracetamol", manufacturer="ABC Pharma"):
        return MedicineCreate(name=name, description="Pain relief medication", manufacturer=manufacturer, price=20.0, quantity=15, expiry_date=date.today() + timedelta(days=30))

    def test_create_list_update_and_delete_medicine(self):
        service.create_medicine(self.payload(), self.admin)
        saved = self.db.medicines.find_one({"name": "Paracetamol"})
        self.assertEqual(len(service.get_medicines(self.admin)), 1)
        service.update_medicine(str(saved["_id"]), MedicineUpdate(quantity=12, price=25.0), self.admin)
        self.assertEqual(self.db.medicines.find_one({"_id": saved["_id"]})["quantity"], 12)
        service.delete_medicine(str(saved["_id"]), self.admin)
        self.assertEqual(self.db.medicines.count_documents({}), 0)
        self.assertEqual(self.db.audit_logs.count_documents({}), 3)

    def test_expiry_duplicate_and_prescription_references_are_rejected(self):
        with self.assertRaises(ValidationError):
            MedicineCreate(name="Paracetamol", description="Pain relief", manufacturer="ABC Pharma", price=20.0, quantity=10, expiry_date=date.today())
        medicine_id = self.add_medicine("Paracetamol", "ABC Pharma")
        with self.assertRaises(HTTPException):
            service.create_medicine(self.payload(), self.admin)
        self.db.prescriptions.insert_one({"medicine_id": medicine_id})
        with self.assertRaises(HTTPException) as linked:
            service.delete_medicine(str(medicine_id), self.admin)
        self.assertEqual(linked.exception.status_code, 409)
        with self.assertRaises(HTTPException) as malformed:
            service.update_medicine("bad-id", MedicineUpdate(quantity=2), self.admin)
        self.assertEqual(malformed.exception.status_code, 400)
