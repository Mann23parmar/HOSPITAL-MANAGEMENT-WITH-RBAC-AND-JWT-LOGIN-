
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.database.connection import (
    doctors_collection,
    users_collection,
    departments_collection
)

from app.core.rbac import require_role
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.services.audit_service import create_audit_log


router = APIRouter()


# ---------------------------------------------------------
# Reusable helper: Validate doctor user
# ---------------------------------------------------------

def get_doctor_user_object_id(user_id: str):

    try:
        user_object_id = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID"
        )

    user = users_collection.find_one(
        {"_id": user_object_id}
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if user["role"] != "doctor":
        raise HTTPException(
            status_code=400,
            detail="Selected user does not have doctor role"
        )

    return user_object_id


# ---------------------------------------------------------
# Reusable helper: Validate department
# ---------------------------------------------------------

def get_department_object_id(department_id: str):

    try:
        department_object_id = ObjectId(department_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid department ID"
        )

    department = departments_collection.find_one(
        {"_id": department_object_id}
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    return department_object_id


# ---------------------------------------------------------
# Reusable helper: Validate doctor ID
# ---------------------------------------------------------

def get_doctor_object_id(doctor_id: str):

    try:
        return ObjectId(doctor_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid doctor ID"
        )


# ---------------------------------------------------------
# Create doctor
# ---------------------------------------------------------

@router.post("/doctors")
def create_doctor(
    doctor: DoctorCreate,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate user
    user_object_id = get_doctor_user_object_id(
        doctor.user_id
    )

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
    department_object_id = get_department_object_id(
        doctor.department_id
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
        "department_id": department_object_id,
        "name": doctor.name,
        "specialization": doctor.specialization,
        "phone": doctor.phone
    }

    result = doctors_collection.insert_one(
        doctor_data
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
    doctor_object_id = get_doctor_object_id(
        doctor_id
    )

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

        user_object_id = get_doctor_user_object_id(
            update_data["user_id"]
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

    # Validate department_id only if provided
    if "department_id" in update_data:

        department_object_id = get_department_object_id(
            update_data["department_id"]
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
    doctors_collection.update_one(
        {"_id": doctor_object_id},
        {
            "$set": update_data
        }
    )

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
    doctor_object_id = get_doctor_object_id(
        doctor_id
    )

    # Find doctor
    doctor = doctors_collection.find_one(
        {"_id": doctor_object_id}
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # Get linked user ID
    user_object_id = doctor["user_id"]

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
    doctors_collection.delete_one(
        {"_id": doctor_object_id}
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
