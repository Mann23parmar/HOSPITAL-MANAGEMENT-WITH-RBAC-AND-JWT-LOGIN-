from fastapi import APIRouter, Depends, Query

from app.core.rbac import require_role
from app.schemas.prescription import PrescriptionCreate, PrescriptionUpdate
from app.services.prescription_service import (
    create_prescription as create_prescription_workflow,
    delete_prescription as delete_prescription_workflow,
    get_prescriptions as get_prescriptions_workflow,
    update_prescription as update_prescription_workflow,
)


router = APIRouter()


@router.post("/prescriptions", status_code=201)
def create_prescription(
    prescription: PrescriptionCreate,
    current_user: dict = Depends(require_role("admin", "doctor")),
):
    return create_prescription_workflow(prescription, current_user)


@router.get("/prescriptions")
def get_prescriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(require_role("admin", "doctor", "nurse")),
):
    return get_prescriptions_workflow(current_user, skip, limit)


@router.put("/prescriptions/{prescription_id}")
def update_prescription(
    prescription_id: str,
    prescription: PrescriptionUpdate,
    current_user: dict = Depends(require_role("admin", "doctor")),
):
    return update_prescription_workflow(prescription_id, prescription, current_user)


@router.delete("/prescriptions/{prescription_id}")
def delete_prescription(
    prescription_id: str,
    current_user: dict = Depends(require_role("admin")),
):
    return delete_prescription_workflow(prescription_id, current_user)
