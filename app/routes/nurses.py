from fastapi import APIRouter, Depends, Query
from app.core.rbac import require_role
from app.schemas.nurse import NurseCreate, NurseUpdate
from app.services.nurses_service import (
    create_nurse as create_nurse_workflow,
    get_nurses as get_nurses_workflow,
    update_nurse as update_nurse_workflow,
    delete_nurse as delete_nurse_workflow,
)


router = APIRouter()


# ---------------------------------------------------------
# Create nurse
# ---------------------------------------------------------


@router.post("/nurses", status_code=201)
def create_nurse(
    nurse: NurseCreate, current_user: dict = Depends(require_role("admin"))
):
    return create_nurse_workflow(nurse, current_user)


@router.get("/nurses")
def get_nurses(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(require_role("admin", "doctor", "nurse")),
):
    return get_nurses_workflow(current_user, skip, limit)


@router.put("/nurses/{nurse_id}")
def update_nurse(
    nurse_id: str,
    nurse: NurseUpdate,
    current_user: dict = Depends(require_role("admin")),
):
    return update_nurse_workflow(nurse_id, nurse, current_user)


@router.delete("/nurses/{nurse_id}")
def delete_nurse(nurse_id: str, current_user: dict = Depends(require_role("admin"))):
    return delete_nurse_workflow(nurse_id, current_user)
