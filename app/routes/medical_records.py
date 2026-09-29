from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.database.connection import (
    medical_records_collection,
    patients_collection,
    doctors_collection,
    appointments_collection
)

from app.core.rbac import require_role
from app.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordUpdate
)


router = APIRouter()


# Create medical record
@router.post("/medical-records")
def create_medical_record(
    record: MedicalRecordCreate,
    current_user: dict = Depends(
        require_role("admin", "doctor")
    )
):

    # Check patient ID
    try:
        patient_object_id = ObjectId(record.patient_id)
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

    # Check doctor ID
    try:
        doctor_object_id = ObjectId(record.doctor_id)
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

    # Check appointment ID
    try:
        appointment_object_id = ObjectId(
            record.appointment_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid appointment ID"
        )

    # Check appointment exists
    appointment = appointments_collection.find_one(
        {"_id": appointment_object_id}
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    # Check appointment belongs to patient
    if appointment["patient_id"] != patient_object_id:
        raise HTTPException(
            status_code=400,
            detail="Appointment does not belong to this patient"
        )

    # Check appointment belongs to doctor
    if appointment["doctor_id"] != doctor_object_id:
        raise HTTPException(
            status_code=400,
            detail="Appointment does not belong to this doctor"
        )

    # Create medical record
    record_data = {
        "patient_id": patient_object_id,
        "doctor_id": doctor_object_id,
        "appointment_id": appointment_object_id,
        "diagnosis": record.diagnosis,
        "treatment": record.treatment,
        "notes": record.notes
    }

    medical_records_collection.insert_one(
        record_data
    )

    return {
        "message": "Medical record created successfully"
    }


# Get all medical records
@router.get("/medical-records")
def get_medical_records(
    current_user: dict = Depends(
        require_role(
            "admin",
            "doctor",
            "nurse"
        )
    )
):

    records = list(
        medical_records_collection.find(
            {},
            {"_id": 0}
        )
    )

    return records


# Update medical record
@router.put("/medical-records/{record_id}")
def update_medical_record(
    record_id: str,
    record: MedicalRecordUpdate,
    current_user: dict = Depends(
        require_role("admin", "doctor")
    )
):

    # Check medical record ID
    try:
        record_object_id = ObjectId(record_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid medical record ID"
        )

    # Check medical record exists
    existing_record = medical_records_collection.find_one(
        {"_id": record_object_id}
    )

    if not existing_record:
        raise HTTPException(
            status_code=404,
            detail="Medical record not found"
        )

    # Check patient ID
    try:
        patient_object_id = ObjectId(record.patient_id)
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

    # Check doctor ID
    try:
        doctor_object_id = ObjectId(record.doctor_id)
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

    # Check appointment ID
    try:
        appointment_object_id = ObjectId(
            record.appointment_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid appointment ID"
        )

    appointment = appointments_collection.find_one(
        {"_id": appointment_object_id}
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    # Check appointment belongs to patient
    if appointment["patient_id"] != patient_object_id:
        raise HTTPException(
            status_code=400,
            detail="Appointment does not belong to this patient"
        )

    # Check appointment belongs to doctor
    if appointment["doctor_id"] != doctor_object_id:
        raise HTTPException(
            status_code=400,
            detail="Appointment does not belong to this doctor"
        )

    medical_records_collection.update_one(
        {"_id": record_object_id},
        {
            "$set": {
                "patient_id": patient_object_id,
                "doctor_id": doctor_object_id,
                "appointment_id": appointment_object_id,
                "diagnosis": record.diagnosis,
                "treatment": record.treatment,
                "notes": record.notes
            }
        }
    )

    return {
        "message": "Medical record updated successfully"
    }


# Delete medical record
@router.delete("/medical-records/{record_id}")
def delete_medical_record(
    record_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Check medical record ID
    try:
        record_object_id = ObjectId(record_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid medical record ID"
        )

    result = medical_records_collection.delete_one(
        {"_id": record_object_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Medical record not found"
        )

    return {
        "message": "Medical record deleted successfully"
    }
    
    
