from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from service_test_support import ServiceIntegrationTestCase
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services import departments_service as service


class DepartmentServiceTests(ServiceIntegrationTestCase):
    def test_department_list_paginates_in_stable_id_order(self):
        for index in range(12):
            self.add_department(f"Page Department {index:02d}")

        first_page = service.get_departments(self.admin)
        self.assertEqual(len(first_page), 10)
        self.assertEqual(first_page[0]["name"], "Page Department 00")
        self.assertEqual(first_page[-1]["name"], "Page Department 09")
        self.assertEqual(
            [item["name"] for item in service.get_departments(self.admin, skip=10, limit=2)],
            ["Page Department 10", "Page Department 11"],
        )
        self.assertEqual(service.get_departments(self.admin, skip=100, limit=10), [])

    def test_create_list_update_and_delete_department(self):
        service.create_department(DepartmentCreate(name="Cardiology", location="3rd Floor", description="Heart care services"), self.admin)
        saved = self.db.departments.find_one({"name": "Cardiology"})
        self.assertEqual(len(service.get_departments(self.admin)), 1)
        service.update_department(str(saved["_id"]), DepartmentUpdate(location="4th Floor"), self.admin)
        self.assertEqual(self.db.departments.find_one({"_id": saved["_id"]})["location"], "4th Floor")
        service.delete_department(str(saved["_id"]), self.admin)
        self.assertEqual(self.db.departments.count_documents({}), 0)
        self.assertEqual(self.db.audit_logs.count_documents({}), 3)

    def test_duplicate_and_staff_reference_prevent_department_changes(self):
        first_id, second_id = self.add_department("Cardiology"), self.add_department("Neurology")
        with self.assertRaises(HTTPException):
            service.create_department(DepartmentCreate(name="Cardiology", location="3rd Floor", description="Heart care services"), self.admin)
        with self.assertRaises(DuplicateKeyError):
            self.db.departments.insert_one({"name": "Cardiology", "location": "Elsewhere", "description": "Unique index race"})
        self.add_doctor(department_id=first_id)
        with self.assertRaises(HTTPException) as error:
            service.delete_department(str(first_id), self.admin)
        self.assertEqual(error.exception.status_code, 409)
        with self.assertRaises(HTTPException) as missing:
            service.update_department("bad-id", DepartmentUpdate(name="Updated"), self.admin)
        self.assertEqual(missing.exception.status_code, 400)
