from fastapi import APIRouter, Depends
from app.core.rbac import require_role
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.services.doctors_service import (
    create_doctor as create_doctor_workflow,
    get_doctors as get_doctors_workflow,
    update_doctor as update_doctor_workflow,
    delete_doctor as delete_doctor_workflow,
)


router = APIRouter()


# ---------------------------------------------------------
# Reusable helper: Validate doctor ID
# ---------------------------------------------------------

# ---------------------------------------------------------
# Create doctor
# ---------------------------------------------------------


@router.post("/doctors", status_code=201)
def create_doctor(
    doctor: DoctorCreate, current_user: dict = Depends(require_role("admin"))
):
    return create_doctor_workflow(doctor, current_user)


@router.get("/doctors")
def get_doctors(
    current_user: dict = Depends(
        require_role("admin", "doctor", "nurse", "receptionist")
    )
):
    return get_doctors_workflow(current_user)


@router.put("/doctors/{doctor_id}")
def update_doctor(
    doctor_id: str,
    doctor: DoctorUpdate,
    current_user: dict = Depends(require_role("admin")),
):
    return update_doctor_workflow(doctor_id, doctor, current_user)


@router.delete("/doctors/{doctor_id}")
def delete_doctor(doctor_id: str, current_user: dict = Depends(require_role("admin"))):
    return delete_doctor_workflow(doctor_id, current_user)
