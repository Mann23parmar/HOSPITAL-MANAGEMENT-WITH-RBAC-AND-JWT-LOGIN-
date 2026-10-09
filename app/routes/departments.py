from fastapi import APIRouter, Depends, HTTPException

from app.core.authorization import get_object_id
from app.database.connection import departments_collection
from app.core.rbac import require_role
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate
)
from app.services.audit_service import create_audit_log


router = APIRouter()


# Reusable department ID validation
# Create department
@router.post("/departments", status_code=201)
def create_department(
    department: DepartmentCreate,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Check if department already exists
    existing_department = departments_collection.find_one(
        {"name": department.name}
    )

    if existing_department:
        raise HTTPException(
            status_code=400,
            detail="Department already exists"
        )

    # Convert Pydantic model to dictionary
    department_data = department.model_dump()

    # Insert department
    result = departments_collection.insert_one(
        department_data
    )

    create_audit_log(
        action="CREATE",
        collection="departments",
        record_id=str(result.inserted_id),
        current_user=current_user
    )

    return {
        "message": "Department created successfully"
    }


# Get all departments
@router.get("/departments")
def get_departments(
    current_user: dict = Depends(
        require_role(
            "admin",
            "doctor",
            "nurse",
            "receptionist"
        )
    )
):

    departments = list(
        departments_collection.find(
            {},
            {"_id": 0}
        )
    )

    return departments


# Update department
@router.put("/departments/{department_id}")
def update_department(
    department_id: str,
    department: DepartmentUpdate,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate department ID
    department_object_id = get_object_id(department_id, "department")

    # Check department exists
    existing_department = departments_collection.find_one(
        {"_id": department_object_id}
    )

    if not existing_department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # Get only fields provided by the user
    update_data = department.model_dump(
        exclude_unset=True
    )

    # Check if at least one field was provided
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="At least one field is required for update"
        )

    # Check duplicate name only if name is being updated
    if "name" in update_data:

        duplicate_department = departments_collection.find_one(
            {
                "name": update_data["name"],
                "_id": {
                    "$ne": department_object_id
                }
            }
        )

        if duplicate_department:
            raise HTTPException(
                status_code=400,
                detail="Another department with this name already exists"
            )

    # Update only provided fields
    departments_collection.update_one(
        {"_id": department_object_id},
        {
            "$set": update_data
        }
    )

    create_audit_log(
        action="UPDATE",
        collection="departments",
        record_id=str(department_object_id),
        current_user=current_user
    )

    return {
        "message": "Department updated successfully"
    }


# Delete department
@router.delete("/departments/{department_id}")
def delete_department(
    department_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate department ID
    department_object_id = get_object_id(department_id, "department")

    result = departments_collection.delete_one(
        {"_id": department_object_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    create_audit_log(
        action="DELETE",
        collection="departments",
        record_id=str(department_object_id),
        current_user=current_user
    )

    return {
        "message": "Department deleted successfully"
    }
