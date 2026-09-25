from fastapi import FastAPI

from app.database.connection import client

from app.routes.auth import router as auth_router
from app.routes.users import router as users_router
from app.routes.patients import router as patients_router
from app.routes.appointments import router as appointments_router
from app.routes.medical_records import router as medical_records_router
from app.routes.pharmacy import router as pharmacy_router
app = FastAPI()


@app.get("/")
def home():

    try:
        client.admin.command("ping")

        return {
            "message": "MongoDB connected successfully"
        }

    except Exception as e:

        return {
            "error": str(e)
        }


app.include_router(auth_router, prefix="/auth")
app.include_router(users_router)
app.include_router(patients_router)
app.include_router(appointments_router)
app.include_router(medical_records_router)
app.include_router(pharmacy_router)

