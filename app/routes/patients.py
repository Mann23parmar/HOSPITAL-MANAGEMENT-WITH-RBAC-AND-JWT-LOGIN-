from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from app.core.authorization import (
    get_current_doctor,
    get_object_id,
    without_pending_references,
)

from app.database.connection import (
    patients_collection,
    appointments_collection,
    medical_records_collection,
    prescriptions_collection,
    patient_vitals_collection,
)

from app.core.rbac import require_role
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.audit_service import create_audit_log


router = APIRouter()


# ---------------------------------------------------------
# Reusable helper: Validate patient ID
# ---------------------------------------------------------

# ---------------------------------------------------------
# Create patient
# ---------------------------------------------------------

@router.post("/patients", status_code=201)
def create_patient(
    patient: PatientCreate,
    current_user: dict = Depends(
        require_role("admin", "receptionist")
    )
):

    # Check duplicate phone number
    existing_patient = patients_collection.find_one(
        {"phone": patient.phone}
    )

    if existing_patient:
        raise HTTPException(
            status_code=400,
            detail="Patient with this phone number already exists"
        )

    # Convert Pydantic model to dictionary
    patient_data = patient.model_dump()

    # Convert date object to string before storing in MongoDB
    patient_data["date_of_birth"] = (
        patient.date_of_birth.isoformat()
    )

    # Store the ID of the logged-in user
    patient_data["created_by"] = ObjectId(
        current_user["user_id"]
    )

    try:
        result = patients_collection.insert_one(patient_data)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="Patient with this phone number already exists",
        )

    create_audit_log(
        action="CREATE",
        collection="patients",
        record_id=str(result.inserted_id),
        current_user=current_user
    )

    return {
        "message": "Patient created successfully"
    }


# ---------------------------------------------------------
# Get all patients
# ---------------------------------------------------------

@router.get("/patients")
def get_patients(
    current_user: dict = Depends(
        require_role(
            "admin",
            "doctor",
            "nurse",
            "receptionist"
        )
    )
):

    # Default: get all patients
    query = {}

    # Doctor: get only patients related
    # to the doctor's appointments
    if current_user["role"] == "doctor":

        # Get logged-in doctor's profile
        doctor = get_current_doctor(
            current_user
        )

        # Find appointments assigned to this doctor
        appointments = appointments_collection.find(
            {
                "doctor_id": doctor["_id"]
            },
            {
                "patient_id": 1
            }
        )

        patient_ids = [
            appointment["patient_id"]
            for appointment in appointments
            if "patient_id" in appointment
        ]

        # Get only related patients
        query = {
            "_id": {
                "$in": patient_ids
            }
        }

    patients = list(
        patients_collection.find(
            query,
            {
                "_id": 0,
                "_pending_reference_writes": 0,
                "_pending_reference_leases": 0,
            }
        )
    )

    # Convert ObjectIds to strings
    for patient in patients:

        if "created_by" in patient:
            patient["created_by"] = str(
                patient["created_by"]
            )

    return patients


# ---------------------------------------------------------
# Update patient
# ---------------------------------------------------------

@router.put("/patients/{patient_id}")
def update_patient(
    patient_id: str,
    patient: PatientUpdate,
    current_user: dict = Depends(
        require_role(
            "admin",
            "receptionist"
        )
    )
):

    # Validate patient ID
    patient_object_id = get_object_id(patient_id, "patient")

    # Check patient exists
    existing_patient = patients_collection.find_one(
        {"_id": patient_object_id}
    )

    if not existing_patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # Get only the fields provided in the request
    update_data = patient.model_dump(
        exclude_unset=True
    )

    # Check if at least one field was provided
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="At least one field is required for update"
        )

    # Check duplicate phone number
    if "phone" in update_data:

        existing_phone = patients_collection.find_one(
            {
                "phone": update_data["phone"],
                "_id": {
                    "$ne": patient_object_id
                }
            }
        )

        if existing_phone:
            raise HTTPException(
                status_code=400,
                detail="Patient with this phone number already exists"
            )

    # Convert date object to string
    if "date_of_birth" in update_data:

        update_data["date_of_birth"] = (
            update_data["date_of_birth"].isoformat()
        )

    # Update only the provided fields
    try:
        update_result = patients_collection.update_one(
            {"_id": patient_object_id},
            {"$set": update_data},
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="Patient with this phone number already exists",
        )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Patient not found")

    create_audit_log(
        action="UPDATE",
        collection="patients",
        record_id=str(patient_object_id),
        current_user=current_user
    )

    return {
        "message": "Patient updated successfully"
    }


# ---------------------------------------------------------
# Delete patient
# ---------------------------------------------------------

@router.delete("/patients/{patient_id}")
def delete_patient(
    patient_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate patient ID
    patient_object_id = get_object_id(patient_id, "patient")

    patient_filter = {"patient_id": patient_object_id}
    if (
        appointments_collection.find_one(patient_filter)
        or medical_records_collection.find_one(patient_filter)
        or prescriptions_collection.find_one(patient_filter)
        or patient_vitals_collection.find_one(patient_filter)
    ):
        raise HTTPException(
            status_code=409,
            detail="Patient cannot be deleted while related records exist",
        )

    result = patients_collection.delete_one(
        without_pending_references(patient_object_id)
    )

    if result.deleted_count == 0:
        if patients_collection.find_one({"_id": patient_object_id}):
            raise HTTPException(
                status_code=409,
                detail="Patient has concurrent references; retry deletion",
            )
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    create_audit_log(
        action="DELETE",
        collection="patients",
        record_id=str(patient_object_id),
        current_user=current_user
    )

    return {
        "message": "Patient deleted successfully"
    }
    
    
