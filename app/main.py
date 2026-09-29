from fastapi import FastAPI

from app.database.connection import client

from app.routes.auth import router as auth_router
from app.routes.users import router as users_router
from app.routes.departments import router as departments_router
from app.routes.doctors import router as doctors_router
from app.routes.nurses import router as nurses_router
from app.routes.patients import router as patients_router
from app.routes.appointments import router as appointments_router
from app.routes.medical_records import router as medical_records_router
from app.routes.medicines import router as medicines_router
from app.routes.prescriptions import router as prescriptions_router
from app.routes.patient_vitals import router as patient_vitals_router


app = FastAPI()


@app.get("/")
def home():
    try:
        client.admin.command("ping")

        return {
            "status": "success",
            "message": "Hospital Management API is running",
            "database": "connected"
        }

    except Exception:
        return {
            "status": "error",
            "message": "Hospital Management API is running",
            "database": "disconnected"
        }

# Authentication
app.include_router(
    auth_router,
    prefix="/auth"
)

# Users
app.include_router(users_router)

# Departments
app.include_router(departments_router)

# Doctors
app.include_router(doctors_router)

# Nurses
app.include_router(nurses_router)

# Patients
app.include_router(patients_router)

# Appointments
app.include_router(appointments_router)

# Medical Records
app.include_router(medical_records_router)

# Medicines
app.include_router(medicines_router)

# Prescriptions
app.include_router(prescriptions_router)

# Patient Vitals
app.include_router(patient_vitals_router)