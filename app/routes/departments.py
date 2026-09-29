from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.database.connection import departments_collection
from app.core.rbac import require_role
from app.schemas.department import DepartmentCreate, DepartmentUpdate


router = APIRouter()


# Create department
@router.post("/departments")
def create_department(
    department: DepartmentCreate,
    current_user: dict = Depends(require_role("admin"))
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

    department_data = department.model_dump()

    departments_collection.insert_one(department_data)

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
    current_user: dict = Depends(require_role("admin"))
):
    try:
        department_object_id = ObjectId(department_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid department ID"
        )

    # Check department exists
    existing_department = departments_collection.find_one(
        {"_id": department_object_id}
    )

    if not existing_department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # Check duplicate name
    duplicate_department = departments_collection.find_one(
        {
            "name": department.name,
            "_id": {"$ne": department_object_id}
        }
    )

    if duplicate_department:
        raise HTTPException(
            status_code=400,
            detail="Another department with this name already exists"
        )

    departments_collection.update_one(
        {"_id": department_object_id},
        {"$set": department.model_dump()}
    )

    return {
        "message": "Department updated successfully"
    }


# Delete department
@router.delete("/departments/{department_id}")
def delete_department(
    department_id: str,
    current_user: dict = Depends(require_role("admin"))
):
    try:
        department_object_id = ObjectId(department_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid department ID"
        )

    result = departments_collection.delete_one(
        {"_id": department_object_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    return {
        "message": "Department deleted successfully"
    }