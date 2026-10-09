
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from app.database.connection import (
    doctors_collection,
    users_collection,
    departments_collection,
    appointments_collection,
    medical_records_collection,
    prescriptions_collection,
)

from app.core.authorization import (
    get_existing_object_id,
    get_object_id,
    protect_references,
    without_pending_references,
    get_user_object_id_for_role,
)
from app.core.rbac import require_role
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.services.audit_service import create_audit_log


router = APIRouter()


# ---------------------------------------------------------
# Reusable helper: Validate doctor ID
# ---------------------------------------------------------

# ---------------------------------------------------------
# Create doctor
# ---------------------------------------------------------

@router.post("/doctors", status_code=201)
def create_doctor(
    doctor: DoctorCreate,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate user
    user_object_id = get_user_object_id_for_role(doctor.user_id, "doctor")

    # Check if this user already has a doctor profile
    existing_doctor = doctors_collection.find_one(
        {"user_id": user_object_id}
    )

    if existing_doctor:
        raise HTTPException(
            status_code=400,
            detail="This user already has a doctor profile"
        )

    # Validate department
    department_object_id = get_existing_object_id(
        doctor.department_id, departments_collection, "department"
    )

    # Check duplicate phone
    existing_phone = doctors_collection.find_one(
        {"phone": doctor.phone}
    )

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Doctor with this phone number already exists"
        )

    doctor_data = {
        "user_id": user_object_id,
        "_unique_user_profile": True,
        "department_id": department_object_id,
        "name": doctor.name,
        "specialization": doctor.specialization,
        "phone": doctor.phone
    }

    try:
        with protect_references(
            (users_collection, user_object_id, "user"),
            (departments_collection, department_object_id, "department"),
        ):
            result = doctors_collection.insert_one(doctor_data)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="Doctor profile or phone number already exists",
        )

    create_audit_log(
        action="CREATE",
        collection="doctors",
        record_id=str(result.inserted_id),
        current_user=current_user
    )

    return {
        "message": "Doctor created successfully"
    }


# ---------------------------------------------------------
# Get all doctors
# ---------------------------------------------------------

@router.get("/doctors")
def get_doctors(
    current_user: dict = Depends(
        require_role(
            "admin",
            "doctor",
            "nurse",
            "receptionist"
        )
    )
):

    doctors = list(
        doctors_collection.aggregate([
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {
                "$lookup": {
                    "from": "departments",
                    "localField": "department_id",
                    "foreignField": "_id",
                    "as": "department"
                }
            },
            {
                "$unwind": {
                    "path": "$user",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$unwind": {
                    "path": "$department",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "user_id": 1,
                    "department_id": 1,
                    "name": 1,
                    "specialization": 1,
                    "phone": 1,
                    "email": "$user.email",
                    "department_name": "$department.name"
                }
            }
        ])
    )

    # Convert ObjectId values to strings
    for doctor in doctors:

        if "user_id" in doctor:
            doctor["user_id"] = str(
                doctor["user_id"]
            )

        if "department_id" in doctor:
            doctor["department_id"] = str(
                doctor["department_id"]
            )

    return doctors


# ---------------------------------------------------------
# Update doctor
# ---------------------------------------------------------

@router.put("/doctors/{doctor_id}")
def update_doctor(
    doctor_id: str,
    doctor: DoctorUpdate,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate doctor ID
    doctor_object_id = get_object_id(doctor_id, "doctor")

    # Check doctor exists
    existing_doctor = doctors_collection.find_one(
        {"_id": doctor_object_id}
    )

    if not existing_doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # Get only fields provided by the user
    update_data = doctor.model_dump(
        exclude_unset=True
    )

    # Check if at least one field was provided
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="At least one field is required for update"
        )

    # Validate user_id only if provided
    if "user_id" in update_data:

        user_object_id = get_user_object_id_for_role(
            update_data["user_id"], "doctor"
        )

        # Check if another doctor already uses this user
        duplicate_user = doctors_collection.find_one(
            {
                "user_id": user_object_id,
                "_id": {
                    "$ne": doctor_object_id
                }
            }
        )

        if duplicate_user:
            raise HTTPException(
                status_code=400,
                detail="This user already has another doctor profile"
            )

        update_data["user_id"] = user_object_id
        update_data["_unique_user_profile"] = True

    # Validate department_id only if provided
    if "department_id" in update_data:

        department_object_id = get_existing_object_id(
            update_data["department_id"], departments_collection, "department"
        )

        update_data["department_id"] = (
            department_object_id
        )

    # Check duplicate phone only if provided
    if "phone" in update_data:

        duplicate_phone = doctors_collection.find_one(
            {
                "phone": update_data["phone"],
                "_id": {
                    "$ne": doctor_object_id
                }
            }
        )

        if duplicate_phone:
            raise HTTPException(
                status_code=400,
                detail="Another doctor already uses this phone number"
            )

    # Update only provided fields
    pending_references = []
    if "department_id" in update_data and update_data["department_id"] != existing_doctor["department_id"]:
        pending_references.append((departments_collection, update_data["department_id"], "department"))
    if "user_id" in update_data and update_data["user_id"] != existing_doctor["user_id"]:
        pending_references.append((users_collection, update_data["user_id"], "user"))

    try:
        with protect_references(*pending_references):
            update_result = doctors_collection.update_one(
                {"_id": doctor_object_id},
                {"$set": update_data},
            )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="Doctor profile or phone number already exists",
        )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Doctor not found")

    create_audit_log(
        action="UPDATE",
        collection="doctors",
        record_id=str(doctor_object_id),
        current_user=current_user
    )

    return {
        "message": "Doctor updated successfully"
    }


# ---------------------------------------------------------
# Delete doctor
# ---------------------------------------------------------

# ---------------------------------------------------------
# Delete doctor
# ---------------------------------------------------------

@router.delete("/doctors/{doctor_id}")
def delete_doctor(
    doctor_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate doctor ID
    doctor_object_id = get_object_id(doctor_id, "doctor")

    # Find doctor
    doctor = doctors_collection.find_one(
        {"_id": doctor_object_id}
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    doctor_filter = {"doctor_id": doctor_object_id}
    if (
        appointments_collection.find_one(doctor_filter)
        or medical_records_collection.find_one(doctor_filter)
        or prescriptions_collection.find_one(doctor_filter)
    ):
        raise HTTPException(
            status_code=409,
            detail="Doctor cannot be deleted while related records exist",
        )

    # Get linked user ID
    user_object_id = doctor["user_id"]
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

    # Delete doctor profile
    delete_result = doctors_collection.delete_one(
        without_pending_references(doctor_object_id)
    )
    if delete_result.deleted_count == 0:
        doctor_still_exists = doctors_collection.find_one({"_id": doctor_object_id})
        if doctor_still_exists and was_active:
            users_collection.update_one(
                {"_id": user_object_id},
                {"$set": {"is_active": True}},
            )
        raise HTTPException(
            status_code=409 if doctor_still_exists else 404,
            detail=(
                "Doctor is being referenced by a concurrent request; retry deletion"
                if doctor_still_exists
                else "Doctor not found"
            ),
        )

    create_audit_log(
        action="DELETE",
        collection="doctors",
        record_id=str(doctor_object_id),
        current_user=current_user
    )

    return {
        "message": "Doctor deleted successfully"
    }
