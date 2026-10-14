from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from app.core.authorization import get_object_id, without_pending_references
from app.database.connection import (
    departments_collection,
    doctors_collection,
    nurses_collection,
)
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services.audit_service import create_audit_log


def create_department(department: DepartmentCreate, current_user: dict):
    existing_department = departments_collection.find_one({"name": department.name})
    if existing_department:
        raise HTTPException(status_code=400, detail="Department already exists")
    department_data = department.model_dump()
    try:
        result = departments_collection.insert_one(department_data)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Department already exists")
    create_audit_log(
        action="CREATE",
        collection="departments",
        record_id=str(result.inserted_id),
        current_user=current_user,
    )
    return {"message": "Department created successfully"}


def get_departments(current_user: dict, skip: int = 0, limit: int = 10):
    departments = list(
        departments_collection.find(
            {},
            {"_id": 0, "_pending_reference_writes": 0, "_pending_reference_leases": 0},
        ).sort("_id", 1).skip(skip).limit(limit)
    )
    return departments


def update_department(
    department_id: str, department: DepartmentUpdate, current_user: dict
):
    department_object_id = get_object_id(department_id, "department")
    existing_department = departments_collection.find_one({"_id": department_object_id})
    if not existing_department:
        raise HTTPException(status_code=404, detail="Department not found")
    update_data = department.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=400, detail="At least one field is required for update"
        )
    if "name" in update_data:
        duplicate_department = departments_collection.find_one(
            {"name": update_data["name"], "_id": {"$ne": department_object_id}}
        )
        if duplicate_department:
            raise HTTPException(
                status_code=400,
                detail="Another department with this name already exists",
            )
    try:
        update_result = departments_collection.update_one(
            {"_id": department_object_id}, {"$set": update_data}
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409, detail="Another department with this name already exists"
        )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Department not found")
    create_audit_log(
        action="UPDATE",
        collection="departments",
        record_id=str(department_object_id),
        current_user=current_user,
    )
    return {"message": "Department updated successfully"}


def delete_department(department_id: str, current_user: dict):
    department_object_id = get_object_id(department_id, "department")
    if doctors_collection.find_one(
        {"department_id": department_object_id}
    ) or nurses_collection.find_one({"department_id": department_object_id}):
        raise HTTPException(
            status_code=409,
            detail="Department cannot be deleted while staff are assigned to it",
        )
    result = departments_collection.delete_one(
        without_pending_references(department_object_id)
    )
    if result.deleted_count == 0:
        if departments_collection.find_one({"_id": department_object_id}):
            raise HTTPException(
                status_code=409,
                detail="Department has concurrent references; retry deletion",
            )
        raise HTTPException(status_code=404, detail="Department not found")
    create_audit_log(
        action="DELETE",
        collection="departments",
        record_id=str(department_object_id),
        current_user=current_user,
    )
    return {"message": "Department deleted successfully"}
