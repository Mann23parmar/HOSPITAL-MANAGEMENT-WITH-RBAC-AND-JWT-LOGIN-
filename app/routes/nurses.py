from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.database.connection import (
    nurses_collection,
    users_collection,
    departments_collection
)

from app.core.rbac import require_role
from app.schemas.nurse import NurseCreate, NurseUpdate


router = APIRouter()


# Create nurse
@router.post("/nurses")
def create_nurse(
    nurse: NurseCreate,
    current_user: dict = Depends(require_role("admin"))
):

    # Check user ID
    try:
        user_object_id = ObjectId(nurse.user_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID"
        )

    # Check user exists
    user = users_collection.find_one(
        {"_id": user_object_id}
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Check user has nurse role
    if user["role"] != "nurse":
        raise HTTPException(
            status_code=400,
            detail="Selected user does not have nurse role"
        )

    # Check department ID
    try:
        department_object_id = ObjectId(nurse.department_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid department ID"
        )

    # Check department exists
    department = departments_collection.find_one(
        {"_id": department_object_id}
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # Check duplicate phone
    existing_phone = nurses_collection.find_one(
        {"phone": nurse.phone}
    )

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Nurse with this phone number already exists"
        )

    nurse_data = {
        "user_id": user_object_id,
        "department_id": department_object_id,
        "name": nurse.name,
        "phone": nurse.phone
    }

    nurses_collection.insert_one(nurse_data)

    return {
        "message": "Nurse created successfully"
    }


# Get all nurses
@router.get("/nurses")
def get_nurses(
    current_user: dict = Depends(
        require_role(
            "admin",
            "doctor",
            "nurse"
        )
    )
):

    nurses = list(
        nurses_collection.find(
            {},
            {"_id": 0}
        )
    )

    return nurses


# Update nurse
@router.put("/nurses/{nurse_id}")
def update_nurse(
    nurse_id: str,
    nurse: NurseUpdate,
    current_user: dict = Depends(require_role("admin"))
):

    # Check nurse ID
    try:
        nurse_object_id = ObjectId(nurse_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid nurse ID"
        )

    # Check nurse exists
    existing_nurse = nurses_collection.find_one(
        {"_id": nurse_object_id}
    )

    if not existing_nurse:
        raise HTTPException(
            status_code=404,
            detail="Nurse not found"
        )

    # Check user ID
    try:
        user_object_id = ObjectId(nurse.user_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID"
        )

    # Check user exists
    user = users_collection.find_one(
        {"_id": user_object_id}
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Check user has nurse role
    if user["role"] != "nurse":
        raise HTTPException(
            status_code=400,
            detail="Selected user does not have nurse role"
        )

    # Check department ID
    try:
        department_object_id = ObjectId(nurse.department_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid department ID"
        )

    # Check department exists
    department = departments_collection.find_one(
        {"_id": department_object_id}
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # Check duplicate phone
    duplicate_phone = nurses_collection.find_one(
        {
            "phone": nurse.phone,
            "_id": {"$ne": nurse_object_id}
        }
    )

    if duplicate_phone:
        raise HTTPException(
            status_code=400,
            detail="Another nurse already uses this phone number"
        )

    nurses_collection.update_one(
        {"_id": nurse_object_id},
        {
            "$set": {
                "user_id": user_object_id,
                "department_id": department_object_id,
                "name": nurse.name,
                "phone": nurse.phone
            }
        }
    )

    return {
        "message": "Nurse updated successfully"
    }


# Delete nurse
@router.delete("/nurses/{nurse_id}")
def delete_nurse(
    nurse_id: str,
    current_user: dict = Depends(require_role("admin"))
):

    try:
        nurse_object_id = ObjectId(nurse_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid nurse ID"
        )

    result = nurses_collection.delete_one(
        {"_id": nurse_object_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Nurse not found"
        )

    return {
        "message": "Nurse deleted successfully"
    }