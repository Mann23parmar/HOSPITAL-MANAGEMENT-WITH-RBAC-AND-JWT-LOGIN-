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
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate user ID
    try:
        user_object_id = ObjectId(
            nurse.user_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID"
        )

    # Check user exists
    user = users_collection.find_one({
        "_id": user_object_id
    })

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

    # Validate department ID
    try:
        department_object_id = ObjectId(
            nurse.department_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid department ID"
        )

    # Check department exists
    department = departments_collection.find_one({
        "_id": department_object_id
    })

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # Check duplicate phone
    existing_phone = nurses_collection.find_one({
        "phone": nurse.phone
    })

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Nurse with this phone number already exists"
        )

    # Prepare nurse document
    nurse_data = {
        "user_id": user_object_id,
        "department_id": department_object_id,
        "name": nurse.name,
        "phone": nurse.phone
    }

    # Insert nurse
    nurses_collection.insert_one(
        nurse_data
    )

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
        nurses_collection.aggregate([
            {
                "$lookup": {
                    "from": "departments",
                    "localField": "department_id",
                    "foreignField": "_id",
                    "as": "department"
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {
                "$unwind": {
                    "path": "$department",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$unwind": {
                    "path": "$user",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "user_id": 1,
                    "department_id": 1,
                    "name": 1,
                    "phone": 1,
                    "email": "$user.email",
                    "department_name": "$department.name"
                }
            }
        ])
    )

    # Convert ObjectIds to strings
    for nurse in nurses:

        if "user_id" in nurse:
            nurse["user_id"] = str(
                nurse["user_id"]
            )

        if "department_id" in nurse:
            nurse["department_id"] = str(
                nurse["department_id"]
            )

    return nurses


# Update nurse
@router.put("/nurses/{nurse_id}")
def update_nurse(
    nurse_id: str,
    nurse: NurseUpdate,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate nurse ID
    try:
        nurse_object_id = ObjectId(
            nurse_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid nurse ID"
        )

    # Check nurse exists
    existing_nurse = nurses_collection.find_one({
        "_id": nurse_object_id
    })

    if not existing_nurse:
        raise HTTPException(
            status_code=404,
            detail="Nurse not found"
        )

    # Get only fields provided by the user
    update_data = nurse.model_dump(
        exclude_unset=True
    )

    # Prevent empty update
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="At least one field is required for update"
        )

    # Validate user ID if provided
    if "user_id" in update_data:

        try:
            user_object_id = ObjectId(
                update_data["user_id"]
            )
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail="Invalid user ID"
            )

        user = users_collection.find_one({
            "_id": user_object_id
        })

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        if user["role"] != "nurse":
            raise HTTPException(
                status_code=400,
                detail="Selected user does not have nurse role"
            )

        update_data["user_id"] = user_object_id

    # Validate department ID if provided
    if "department_id" in update_data:

        try:
            department_object_id = ObjectId(
                update_data["department_id"]
            )
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail="Invalid department ID"
            )

        department = departments_collection.find_one({
            "_id": department_object_id
        })

        if not department:
            raise HTTPException(
                status_code=404,
                detail="Department not found"
            )

        update_data["department_id"] = department_object_id

    # Check duplicate phone if provided
    if "phone" in update_data:

        duplicate_phone = nurses_collection.find_one({
            "phone": update_data["phone"],
            "_id": {
                "$ne": nurse_object_id
            }
        })

        if duplicate_phone:
            raise HTTPException(
                status_code=400,
                detail="Another nurse already uses this phone number"
            )

    # Update only provided fields
    nurses_collection.update_one(
        {"_id": nurse_object_id},
        {"$set": update_data}
    )

    return {
        "message": "Nurse updated successfully"
    }


# Delete nurse
@router.delete("/nurses/{nurse_id}")
def delete_nurse(
    nurse_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate nurse ID
    try:
        nurse_object_id = ObjectId(
            nurse_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid nurse ID"
        )

    # Delete nurse
    result = nurses_collection.delete_one({
        "_id": nurse_object_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Nurse not found"
        )

    return {
        "message": "Nurse deleted successfully"
    }