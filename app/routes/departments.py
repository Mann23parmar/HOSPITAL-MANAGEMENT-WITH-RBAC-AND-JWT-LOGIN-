from fastapi import APIRouter, Depends, Query
from app.core.rbac import require_role
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services.departments_service import (
    create_department as create_department_workflow,
    get_departments as get_departments_workflow,
    update_department as update_department_workflow,
    delete_department as delete_department_workflow,
)


router = APIRouter()


# Reusable department ID validation
# Create department


@router.post("/departments", status_code=201)
def create_department(
    department: DepartmentCreate, current_user: dict = Depends(require_role("admin"))
):
    return create_department_workflow(department, current_user)


@router.get("/departments")
def get_departments(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(
        require_role("admin", "doctor", "nurse", "receptionist")
    )
):
    return get_departments_workflow(current_user, skip, limit)


@router.put("/departments/{department_id}")
def update_department(
    department_id: str,
    department: DepartmentUpdate,
    current_user: dict = Depends(require_role("admin")),
):
    return update_department_workflow(department_id, department, current_user)


@router.delete("/departments/{department_id}")
def delete_department(
    department_id: str, current_user: dict = Depends(require_role("admin"))
):
    return delete_department_workflow(department_id, current_user)
