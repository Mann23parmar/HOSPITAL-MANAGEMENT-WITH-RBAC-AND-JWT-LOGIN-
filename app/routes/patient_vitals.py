from fastapi import APIRouter, Depends, Query
from app.core.rbac import require_role
from app.schemas.patient_vitals import PatientVitalsCreate, PatientVitalsUpdate
from app.services.patient_vitals_service import (
    create_patient_vitals as create_patient_vitals_workflow,
    get_patient_vitals as get_patient_vitals_workflow,
    update_patient_vitals as update_patient_vitals_workflow,
    delete_patient_vitals as delete_patient_vitals_workflow,
)


router = APIRouter()


# Reusable nurse validation


@router.post("/patient-vitals", status_code=201)
def create_patient_vitals(
    vitals: PatientVitalsCreate,
    current_user: dict = Depends(require_role("admin", "nurse")),
):
    return create_patient_vitals_workflow(vitals, current_user)


@router.get("/patient-vitals")
def get_patient_vitals(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(require_role("admin", "doctor", "nurse"))
):
    return get_patient_vitals_workflow(current_user, skip, limit)


@router.put("/patient-vitals/{vitals_id}")
def update_patient_vitals(
    vitals_id: str,
    vitals: PatientVitalsUpdate,
    current_user: dict = Depends(require_role("admin", "nurse")),
):
    return update_patient_vitals_workflow(vitals_id, vitals, current_user)


@router.delete("/patient-vitals/{vitals_id}")
def delete_patient_vitals(
    vitals_id: str, current_user: dict = Depends(require_role("admin"))
):
    return delete_patient_vitals_workflow(vitals_id, current_user)
