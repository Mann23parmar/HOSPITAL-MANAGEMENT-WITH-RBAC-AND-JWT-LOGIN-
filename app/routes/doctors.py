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


router = APIRouter()


# Create doctor
@router.post("/doctors")
def create_doctor(
    doctor: DoctorCreate,
    current_user: dict = Depends(require_role("admin"))
):

    # Check user ID
    try:
        user_object_id = ObjectId(doctor.user_id)
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

    # Check user has doctor role
    if user["role"] != "doctor":
        raise HTTPException(
            status_code=400,
            detail="Selected user does not have doctor role"
        )

    # Check department ID
    try:
        department_object_id = ObjectId(doctor.department_id)
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

    doctors_collection.insert_one(doctor_data)

    return {
        "message": "Doctor created successfully"
    }


# Get all doctors
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
        doctors_collection.find(
            {},
            {"_id": 0}
        )
    )

    # Convert MongoDB ObjectId values to strings
    for doctor in doctors:
        doctor["user_id"] = str(doctor["user_id"])
        doctor["department_id"] = str(doctor["department_id"])

    return doctors


# Update doctor
@router.put("/doctors/{doctor_id}")
def update_doctor(
    doctor_id: str,
    doctor: DoctorUpdate,
    current_user: dict = Depends(require_role("admin"))
):

    # Check doctor ID
    try:
        doctor_object_id = ObjectId(doctor_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid doctor ID"
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

    # Check user ID
    try:
        user_object_id = ObjectId(doctor.user_id)
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

    # Check user has doctor role
    if user["role"] != "doctor":
        raise HTTPException(
            status_code=400,
            detail="Selected user does not have doctor role"
        )

    # Check department ID
    try:
        department_object_id = ObjectId(doctor.department_id)
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
    duplicate_phone = doctors_collection.find_one(
        {
            "phone": doctor.phone,
            "_id": {"$ne": doctor_object_id}
        }
    )

    if duplicate_phone:
        raise HTTPException(
            status_code=400,
            detail="Another doctor already uses this phone number"
        )

    doctors_collection.update_one(
        {"_id": doctor_object_id},
        {
            "$set": {
                "user_id": user_object_id,
                "department_id": department_object_id,
                "name": doctor.name,
                "specialization": doctor.specialization,
                "phone": doctor.phone
            }
        }
    )

    return {
        "message": "Doctor updated successfully"
    }


# Delete doctor
@router.delete("/doctors/{doctor_id}")
def delete_doctor(
    doctor_id: str,
    current_user: dict = Depends(require_role("admin"))
):

    try:
        doctor_object_id = ObjectId(doctor_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid doctor ID"
        )

    result = doctors_collection.delete_one(
        {"_id": doctor_object_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    return {
        "message": "Doctor deleted successfully"
    }