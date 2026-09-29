from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.database.connection import (
    prescriptions_collection,
    patients_collection,
    doctors_collection,
    medical_records_collection,
    medicines_collection
)

from app.core.rbac import require_role
from app.schemas.prescription import (
    PrescriptionCreate,
    PrescriptionUpdate
)


router = APIRouter()


# Create prescription
@router.post("/prescriptions")
def create_prescription(
    prescription: PrescriptionCreate,
    current_user: dict = Depends(
        require_role("admin", "doctor")
    )
):

    # Validate patient ID
    try:
        patient_object_id = ObjectId(
            prescription.patient_id
        )
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

    # Validate doctor ID
    try:
        doctor_object_id = ObjectId(
            prescription.doctor_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid doctor ID"
        )

    # Check doctor exists
    doctor = doctors_collection.find_one(
        {"_id": doctor_object_id}
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # Validate medical record ID
    try:
        medical_record_object_id = ObjectId(
            prescription.medical_record_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid medical record ID"
        )

    # Check medical record exists
    medical_record = medical_records_collection.find_one(
        {"_id": medical_record_object_id}
    )

    if not medical_record:
        raise HTTPException(
            status_code=404,
            detail="Medical record not found"
        )

    # Check medical record belongs to patient
    if medical_record["patient_id"] != patient_object_id:
        raise HTTPException(
            status_code=400,
            detail="Medical record does not belong to this patient"
        )

    # Check medical record belongs to doctor
    if medical_record["doctor_id"] != doctor_object_id:
        raise HTTPException(
            status_code=400,
            detail="Medical record does not belong to this doctor"
        )

    # Validate medicine ID
    try:
        medicine_object_id = ObjectId(
            prescription.medicine_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid medicine ID"
        )

    # Check medicine exists
    medicine = medicines_collection.find_one(
        {"_id": medicine_object_id}
    )

    if not medicine:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    # Prepare prescription document
    prescription_data = {
        "patient_id": patient_object_id,
        "doctor_id": doctor_object_id,
        "medical_record_id": medical_record_object_id,
        "medicine_id": medicine_object_id,
        "dosage": prescription.dosage,
        "frequency": prescription.frequency,
        "duration": prescription.duration,
        "instructions": prescription.instructions
    }

    # Insert into MongoDB
    prescriptions_collection.insert_one(
        prescription_data
    )

    return {
        "message": "Prescription created successfully"
    }


# Get all prescriptions
@router.get("/prescriptions")
def get_prescriptions(
    current_user: dict = Depends(
        require_role(
            "admin",
            "doctor",
            "nurse"
        )
    )
):

    prescriptions = list(
        prescriptions_collection.find(
            {},
            {"_id": 0}
        )
    )

    return prescriptions


# Update prescription
@router.put("/prescriptions/{prescription_id}")
def update_prescription(
    prescription_id: str,
    prescription: PrescriptionUpdate,
    current_user: dict = Depends(
        require_role("admin", "doctor")
    )
):

    # Validate prescription ID
    try:
        prescription_object_id = ObjectId(
            prescription_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid prescription ID"
        )

    # Check prescription exists
    existing_prescription = prescriptions_collection.find_one(
        {"_id": prescription_object_id}
    )

    if not existing_prescription:
        raise HTTPException(
            status_code=404,
            detail="Prescription not found"
        )

    # Validate patient ID
    try:
        patient_object_id = ObjectId(
            prescription.patient_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid patient ID"
        )

    patient = patients_collection.find_one(
        {"_id": patient_object_id}
    )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # Validate doctor ID
    try:
        doctor_object_id = ObjectId(
            prescription.doctor_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid doctor ID"
        )

    doctor = doctors_collection.find_one(
        {"_id": doctor_object_id}
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # Validate medical record ID
    try:
        medical_record_object_id = ObjectId(
            prescription.medical_record_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid medical record ID"
        )

    medical_record = medical_records_collection.find_one(
        {"_id": medical_record_object_id}
    )

    if not medical_record:
        raise HTTPException(
            status_code=404,
            detail="Medical record not found"
        )

    # Check medical record relationship
    if medical_record["patient_id"] != patient_object_id:
        raise HTTPException(
            status_code=400,
            detail="Medical record does not belong to this patient"
        )

    if medical_record["doctor_id"] != doctor_object_id:
        raise HTTPException(
            status_code=400,
            detail="Medical record does not belong to this doctor"
        )

    # Validate medicine ID
    try:
        medicine_object_id = ObjectId(
            prescription.medicine_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid medicine ID"
        )

    medicine = medicines_collection.find_one(
        {"_id": medicine_object_id}
    )

    if not medicine:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    # Update prescription
    prescriptions_collection.update_one(
        {"_id": prescription_object_id},
        {
            "$set": {
                "patient_id": patient_object_id,
                "doctor_id": doctor_object_id,
                "medical_record_id": medical_record_object_id,
                "medicine_id": medicine_object_id,
                "dosage": prescription.dosage,
                "frequency": prescription.frequency,
                "duration": prescription.duration,
                "instructions": prescription.instructions
            }
        }
    )

    return {
        "message": "Prescription updated successfully"
    }


# Delete prescription
@router.delete("/prescriptions/{prescription_id}")
def delete_prescription(
    prescription_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate prescription ID
    try:
        prescription_object_id = ObjectId(
            prescription_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid prescription ID"
        )

    # Delete prescription
    result = prescriptions_collection.delete_one(
        {"_id": prescription_object_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Prescription not found"
        )

    return {
        "message": "Prescription deleted successfully"
    }
    
