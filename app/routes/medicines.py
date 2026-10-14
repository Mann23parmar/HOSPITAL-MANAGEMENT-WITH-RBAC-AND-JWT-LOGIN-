from fastapi import APIRouter, Depends, Query
from app.core.rbac import require_role
from app.schemas.medicine import MedicineCreate, MedicineUpdate
from app.services.medicines_service import (
    create_medicine as create_medicine_workflow,
    get_medicines as get_medicines_workflow,
    update_medicine as update_medicine_workflow,
    delete_medicine as delete_medicine_workflow,
)


router = APIRouter()


# ---------------------------------------------------------
# Reusable helper: Validate medicine ID
# ---------------------------------------------------------


@router.post("/medicines", status_code=201)
def create_medicine(
    medicine: MedicineCreate, current_user: dict = Depends(require_role("admin"))
):
    return create_medicine_workflow(medicine, current_user)


@router.get("/medicines")
def get_medicines(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(
        require_role("admin", "doctor", "nurse", "receptionist")
    )
):
    return get_medicines_workflow(current_user, skip, limit)


@router.put("/medicines/{medicine_id}")
def update_medicine(
    medicine_id: str,
    medicine: MedicineUpdate,
    current_user: dict = Depends(require_role("admin")),
):
    return update_medicine_workflow(medicine_id, medicine, current_user)


@router.delete("/medicines/{medicine_id}")
def delete_medicine(
    medicine_id: str, current_user: dict = Depends(require_role("admin"))
):
    return delete_medicine_workflow(medicine_id, current_user)
