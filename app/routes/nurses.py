
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from app.database.connection import (
    nurses_collection,
    users_collection,
    departments_collection,
    patient_vitals_collection,
)

from app.core.rbac import require_role
from app.core.authorization import (
    get_existing_object_id,
    get_object_id,
    protect_references,
    without_pending_references,
    get_user_object_id_for_role,
)
from app.schemas.nurse import NurseCreate, NurseUpdate
from app.services.audit_service import create_audit_log


router = APIRouter()


# ---------------------------------------------------------
# Create nurse
# ---------------------------------------------------------

@router.post("/nurses", status_code=201)
def create_nurse(
    nurse: NurseCreate,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate user
    user_object_id = get_user_object_id_for_role(nurse.user_id, "nurse")

    # Check if this user already has a nurse profile
    existing_nurse = nurses_collection.find_one(
        {"user_id": user_object_id}
    )

    if existing_nurse:
        raise HTTPException(
            status_code=400,
            detail="This user already has a nurse profile"
        )

    # Validate department
    department_object_id = get_existing_object_id(
        nurse.department_id, departments_collection, "department"
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
    try:
        with protect_references(
            (users_collection, user_object_id, "user"),
            (departments_collection, department_object_id, "department"),
        ):
            result = nurses_collection.insert_one(nurse_data)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="Nurse profile or phone number already exists",
        )

    create_audit_log(
        action="CREATE",
        collection="nurses",
        record_id=str(result.inserted_id),
        current_user=current_user
    )

    return {
        "message": "Nurse created successfully"
    }


# ---------------------------------------------------------
# Get all nurses
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Update nurse
# ---------------------------------------------------------

@router.put("/nurses/{nurse_id}")
def update_nurse(
    nurse_id: str,
    nurse: NurseUpdate,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate nurse ID
    nurse_object_id = get_object_id(nurse_id, "nurse")

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

        user_object_id = get_user_object_id_for_role(
            update_data["user_id"], "nurse"
        )

        # Check if another nurse already uses this user
        duplicate_user = nurses_collection.find_one(
            {
                "user_id": user_object_id,
                "_id": {
                    "$ne": nurse_object_id
                }
            }
        )

        if duplicate_user:
            raise HTTPException(
                status_code=400,
                detail="This user already has another nurse profile"
            )

        update_data["user_id"] = user_object_id

    # Validate department ID if provided
    if "department_id" in update_data:

        department_object_id = get_existing_object_id(
            update_data["department_id"], departments_collection, "department"
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
    pending_references = []
    if "department_id" in update_data and update_data["department_id"] != existing_nurse["department_id"]:
        pending_references.append((departments_collection, update_data["department_id"], "department"))
    if "user_id" in update_data and update_data["user_id"] != existing_nurse["user_id"]:
        pending_references.append((users_collection, update_data["user_id"], "user"))

    try:
        with protect_references(*pending_references):
            update_result = nurses_collection.update_one(
                {"_id": nurse_object_id},
                {"$set": update_data},
            )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="Nurse profile or phone number already exists",
        )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Nurse not found")

    create_audit_log(
        action="UPDATE",
        collection="nurses",
        record_id=str(nurse_object_id),
        current_user=current_user
    )

    return {
        "message": "Nurse updated successfully"
    }


# ---------------------------------------------------------
# Delete nurse
# ---------------------------------------------------------
# ---------------------------------------------------------
# Delete nurse
# ---------------------------------------------------------

@router.delete("/nurses/{nurse_id}")
def delete_nurse(
    nurse_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate nurse ID
    nurse_object_id = get_object_id(nurse_id, "nurse")

    # Find nurse
    nurse = nurses_collection.find_one({
        "_id": nurse_object_id
    })

    if not nurse:
        raise HTTPException(
            status_code=404,
            detail="Nurse not found"
        )

    if patient_vitals_collection.find_one({"nurse_id": nurse_object_id}):
        raise HTTPException(
            status_code=409,
            detail="Nurse cannot be deleted while related vitals exist",
        )

    # Get linked user ID
    user_object_id = nurse["user_id"]
    linked_user = users_collection.find_one({"_id": user_object_id})
    was_active = linked_user.get("is_active", True) if linked_user else False

    # Deactivate user account
    users_collection.update_one(
        {"_id": user_object_id},
        {
            "$set": {
                "is_active": False
            }
        }
    )

    create_audit_log(
        action="UPDATE",
        collection="users",
        record_id=str(user_object_id),
        current_user=current_user
    )

    # Delete nurse profile
    delete_result = nurses_collection.delete_one(
        without_pending_references(nurse_object_id)
    )
    if delete_result.deleted_count == 0:
        nurse_still_exists = nurses_collection.find_one({"_id": nurse_object_id})
        if nurse_still_exists and was_active:
            users_collection.update_one(
                {"_id": user_object_id},
                {"$set": {"is_active": True}},
            )
        raise HTTPException(
            status_code=409 if nurse_still_exists else 404,
            detail=(
                "Nurse is being referenced by a concurrent request; retry deletion"
                if nurse_still_exists
                else "Nurse not found"
            ),
        )

    create_audit_log(
        action="DELETE",
        collection="nurses",
        record_id=str(nurse_object_id),
        current_user=current_user
    )

    return {
        "message": "Nurse deleted successfully"
    }
