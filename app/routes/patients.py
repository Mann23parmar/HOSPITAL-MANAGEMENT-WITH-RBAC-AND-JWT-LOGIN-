from fastapi import APIRouter, Depends
from app.core.rbac import require_role
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.patients_service import (
    create_patient as create_patient_workflow,
    get_patients as get_patients_workflow,
    update_patient as update_patient_workflow,
    delete_patient as delete_patient_workflow,
)


router = APIRouter()


# ---------------------------------------------------------
# Reusable helper: Validate patient ID
# ---------------------------------------------------------

# ---------------------------------------------------------
# Create patient
# ---------------------------------------------------------


@router.post("/patients", status_code=201)
def create_patient(
    patient: PatientCreate,
    current_user: dict = Depends(require_role("admin", "receptionist")),
):
    return create_patient_workflow(patient, current_user)


@router.get("/patients")
def get_patients(
    current_user: dict = Depends(
        require_role("admin", "doctor", "nurse", "receptionist")
    )
):
    return get_patients_workflow(current_user)


@router.put("/patients/{patient_id}")
def update_patient(
    patient_id: str,
    patient: PatientUpdate,
    current_user: dict = Depends(require_role("admin", "receptionist")),
):
    return update_patient_workflow(patient_id, patient, current_user)


@router.delete("/patients/{patient_id}")
def delete_patient(
    patient_id: str, current_user: dict = Depends(require_role("admin"))
):
    return delete_patient_workflow(patient_id, current_user)
