from fastapi import APIRouter, Depends, Query
from app.core.rbac import require_role
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordUpdate
from app.services.medical_records_service import (
    create_medical_record as create_medical_record_workflow,
    get_medical_records as get_medical_records_workflow,
    update_medical_record as update_medical_record_workflow,
    delete_medical_record as delete_medical_record_workflow,
)


router = APIRouter()


# =========================================================
# Reusable validation functions
# =========================================================


@router.post("/medical-records", status_code=201)
def create_medical_record(
    record: MedicalRecordCreate,
    current_user: dict = Depends(require_role("admin", "doctor")),
):
    return create_medical_record_workflow(record, current_user)


@router.get("/medical-records")
def get_medical_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(require_role("admin", "doctor", "nurse"))
):
    return get_medical_records_workflow(current_user, skip, limit)


@router.put("/medical-records/{record_id}")
def update_medical_record(
    record_id: str,
    record: MedicalRecordUpdate,
    current_user: dict = Depends(require_role("admin", "doctor")),
):
    return update_medical_record_workflow(record_id, record, current_user)


@router.delete("/medical-records/{record_id}")
def delete_medical_record(
    record_id: str, current_user: dict = Depends(require_role("admin"))
):
    return delete_medical_record_workflow(record_id, current_user)
