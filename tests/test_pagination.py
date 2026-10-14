import asyncio
from urllib.parse import urlencode

from fastapi import FastAPI

from service_test_support import ServiceIntegrationTestCase
from app.routes import (
    appointments as appointments_route,
    doctors as doctors_route,
    medical_records as medical_records_route,
    medicines as medicines_route,
    nurses as nurses_route,
    patients as patients_route,
    prescriptions as prescriptions_route,
)
from app.services import prescription_service
from app.services.auth_service import get_current_user
from app.services import (
    appointments_service,
    doctors_service,
    medical_records_service,
    medicines_service,
    nurses_service,
    patients_service,
)


class PaginationTests(ServiceIntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.prescription_originals = {}
        for name in ("prescriptions", "patients", "doctors", "medical_records", "medicines"):
            attr = f"{name}_collection"
            cls.prescription_originals[attr] = getattr(prescription_service, attr)
            setattr(prescription_service, attr, cls.db[name])

    @classmethod
    def tearDownClass(cls):
        for attr, original in cls.prescription_originals.items():
            setattr(prescription_service, attr, original)
        super().tearDownClass()

    def test_all_list_services_apply_default_custom_and_empty_pages(self):
        services = (
            (patients_service.get_patients, "patients", "name"),
            (doctors_service.get_doctors, "doctors", "name"),
            (nurses_service.get_nurses, "nurses", "name"),
            (appointments_service.get_appointments, "appointments", "reason"),
            (medical_records_service.get_medical_records, "medical_records", "diagnosis"),
            (medicines_service.get_medicines, "medicines", "name"),
            (prescription_service.get_prescriptions, "prescriptions", "dosage"),
        )
        for _service, collection_name, field in services:
            for index in range(12):
                document = {field: f"{collection_name}-{index:02d}"}
                if collection_name == "patients":
                    document["phone"] = f"9{index:09d}"
                elif collection_name in ("doctors", "nurses"):
                    document["phone"] = f"8{index:09d}"
                self.db[collection_name].insert_one(document)

        for get_items, collection_name, field in services:
            with self.subTest(collection=collection_name):
                first_page = get_items(self.admin)
                self.assertEqual(len(first_page), 10)
                self.assertEqual(first_page[0][field], f"{collection_name}-00")
                self.assertEqual(first_page[-1][field], f"{collection_name}-09")

                second_page = get_items(self.admin, skip=10, limit=2)
                self.assertEqual(
                    [item[field] for item in second_page],
                    [f"{collection_name}-10", f"{collection_name}-11"],
                )
                self.assertEqual(get_items(self.admin, skip=100, limit=10), [])

    def test_doctor_scoped_lists_remain_filtered_before_pagination(self):
        own_user, other_user = self.add_user("doctor"), self.add_user("doctor")
        own_doctor, other_doctor = self.add_doctor(own_user), self.add_doctor(other_user)
        own_patient, other_patient = self.add_patient(), self.add_patient()
        own_appointment = self.add_appointment(own_patient, own_doctor)
        self.add_appointment(other_patient, other_doctor, when="11:30:00")
        self.db.medical_records.insert_many(
            [
                {"doctor_id": own_doctor, "patient_id": own_patient, "diagnosis": "own"},
                {"doctor_id": other_doctor, "patient_id": other_patient, "diagnosis": "other"},
            ]
        )
        self.db.prescriptions.insert_many(
            [
                {"doctor_id": own_doctor, "patient_id": own_patient, "dosage": "own"},
                {"doctor_id": other_doctor, "patient_id": other_patient, "dosage": "other"},
            ]
        )
        actor = {"user_id": str(own_user), "role": "doctor", "email": "doctor@example.test"}

        self.assertEqual(len(patients_service.get_patients(actor, skip=0, limit=1)), 1)
        self.assertEqual(
            appointments_service.get_appointments(actor, skip=0, limit=10)[0]["patient_id"],
            str(own_patient),
        )
        self.assertEqual(
            [item["diagnosis"] for item in medical_records_service.get_medical_records(actor)],
            ["own"],
        )
        self.assertEqual(
            [item["dosage"] for item in prescription_service.get_prescriptions(actor)],
            ["own"],
        )
        self.assertIsNotNone(own_appointment)

    def test_all_list_routes_validate_pagination_query_parameters(self):
        routes = (
            appointments_route.router,
            doctors_route.router,
            medical_records_route.router,
            medicines_route.router,
            nurses_route.router,
            patients_route.router,
            prescriptions_route.router,
        )
        app = FastAPI()
        for router in routes:
            app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: self.admin

        async def request(path, params):
            messages = []
            query_string = urlencode(params).encode()

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                messages.append(message)

            scope = {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": query_string,
                "root_path": "",
                "headers": [(b"host", b"testserver")],
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
            }
            await app(scope, receive, send)
            return messages[0]["status"]

        for path in (
            "/appointments", "/doctors", "/medical-records", "/medicines",
            "/nurses", "/patients", "/prescriptions",
        ):
            with self.subTest(path=path, parameter="skip"):
                self.assertEqual(asyncio.run(request(path, {"skip": -1})), 422)
            with self.subTest(path=path, parameter="limit-low"):
                self.assertEqual(asyncio.run(request(path, {"limit": 0})), 422)
            with self.subTest(path=path, parameter="limit-high"):
                self.assertEqual(asyncio.run(request(path, {"limit": 101})), 422)

