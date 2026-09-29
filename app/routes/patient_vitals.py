from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.database.connection import (
    patient_vitals_collection,
    patients_collection,
    nurses_collection,
    users_collection
)

from app.core.rbac import require_role
from app.schemas.patient_vitals import (
    PatientVitalsCreate,
    PatientVitalsUpdate
)


router = APIRouter()


# Create patient vitals
@router.post("/patient-vitals")
def create_patient_vitals(
    vitals: PatientVitalsCreate,
    current_user: dict = Depends(
        require_role("admin", "nurse")
    )
):

    # Validate patient ID
    try:
        patient_object_id = ObjectId(vitals.patient_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid patient ID"
        )

    # Check patient exists
    patient = patients_collection.find_one(
        {"_id": patient_object_id}
    )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # Validate nurse ID
    try:
        nurse_object_id = ObjectId(vitals.nurse_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid nurse ID"
        )

    # Check nurse exists
    nurse = nurses_collection.find_one(
        {"_id": nurse_object_id}
    )

    if not nurse:
        raise HTTPException(
            status_code=404,
            detail="Nurse not found"
        )

    # Check linked user exists
    nurse_user = users_collection.find_one(
        {"_id": nurse["user_id"]}
    )

    if not nurse_user:
        raise HTTPException(
            status_code=404,
            detail="Nurse user account not found"
        )

    # Check linked user has nurse role
    if nurse_user["role"] != "nurse":
        raise HTTPException(
            status_code=400,
            detail="Selected user does not have nurse role"
        )

    # Prepare vitals document
    vitals_data = {
        "patient_id": patient_object_id,
        "nurse_id": nurse_object_id,
        "blood_pressure": vitals.blood_pressure,
        "temperature": vitals.temperature,
        "pulse_rate": vitals.pulse_rate,
        "weight": vitals.weight
    }

    # Insert into MongoDB
    patient_vitals_collection.insert_one(
        vitals_data
    )

    return {
        "message": "Patient vitals recorded successfully"
    }


# Get all patient vitals
@router.get("/patient-vitals")
def get_patient_vitals(
    current_user: dict = Depends(
        require_role(
            "admin",
            "doctor",
            "nurse"
        )
    )
):

    vitals = list(
        patient_vitals_collection.find(
            {},
            {"_id": 0}
        )
    )

    return vitals


# Update patient vitals
@router.put("/patient-vitals/{vitals_id}")
def update_patient_vitals(
    vitals_id: str,
    vitals: PatientVitalsUpdate,
    current_user: dict = Depends(
        require_role("admin", "nurse")
    )
):

    # Validate vitals ID
    try:
        vitals_object_id = ObjectId(vitals_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid vitals ID"
        )

    # Check vitals exist
    existing_vitals = patient_vitals_collection.find_one(
        {"_id": vitals_object_id}
    )

    if not existing_vitals:
        raise HTTPException(
            status_code=404,
            detail="Patient vitals not found"
        )

    # Validate patient ID
    try:
        patient_object_id = ObjectId(vitals.patient_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid patient ID"
        )

    # Check patient exists
    patient = patients_collection.find_one(
        {"_id": patient_object_id}
    )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # Validate nurse ID
    try:
        nurse_object_id = ObjectId(vitals.nurse_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid nurse ID"
        )

    # Check nurse exists
    nurse = nurses_collection.find_one(
        {"_id": nurse_object_id}
    )

    if not nurse:
        raise HTTPException(
            status_code=404,
            detail="Nurse not found"
        )

    # Check linked nurse user exists
    nurse_user = users_collection.find_one(
        {"_id": nurse["user_id"]}
    )

    if not nurse_user:
        raise HTTPException(
            status_code=404,
            detail="Nurse user account not found"
        )

    # Check linked user has nurse role
    if nurse_user["role"] != "nurse":
        raise HTTPException(
            status_code=400,
            detail="Selected user does not have nurse role"
        )

    # Update vitals
    patient_vitals_collection.update_one(
        {"_id": vitals_object_id},
        {
            "$set": {
                "patient_id": patient_object_id,
                "nurse_id": nurse_object_id,
                "blood_pressure": vitals.blood_pressure,
                "temperature": vitals.temperature,
                "pulse_rate": vitals.pulse_rate,
                "weight": vitals.weight
            }
        }
    )

    return {
        "message": "Patient vitals updated successfully"
    }


# Delete patient vitals
@router.delete("/patient-vitals/{vitals_id}")
def delete_patient_vitals(
    vitals_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate vitals ID
    try:
        vitals_object_id = ObjectId(vitals_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid vitals ID"
        )

    # Delete vitals
    result = patient_vitals_collection.delete_one(
        {"_id": vitals_object_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Patient vitals not found"
        )

    return {
        "message": "Patient vitals deleted successfully"
    }