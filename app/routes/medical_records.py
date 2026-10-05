from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.core.authorization import get_current_doctor
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


# =========================================================
# Reusable validation functions
# =========================================================

def get_patient_object_id(patient_id: str):
    try:
        patient_object_id = ObjectId(patient_id)
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

    return patient_object_id


def get_doctor_object_id(doctor_id: str):
    try:
        doctor_object_id = ObjectId(doctor_id)
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

    return doctor_object_id


def get_appointment_object_id(appointment_id: str):
    try:
        appointment_object_id = ObjectId(appointment_id)
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

    return appointment_object_id


# =========================================================
# Create medical record
# =========================================================

@router.post("/medical-records")
def create_medical_record(
    record: MedicalRecordCreate,
    current_user: dict = Depends(
        require_role("admin", "doctor")
    )
):

    # Validate patient
    patient_object_id = get_patient_object_id(
        record.patient_id
    )

    # Validate doctor
    doctor_object_id = get_doctor_object_id(
        record.doctor_id
    )

    # Validate appointment
    appointment_object_id = get_appointment_object_id(
        record.appointment_id
    )

    appointment = appointments_collection.find_one(
        {"_id": appointment_object_id}
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

    # If doctor is creating the record,
    # make sure it is their own doctor profile
    if current_user["role"] == "doctor":

        current_doctor = get_current_doctor(current_user)

        if doctor_object_id != current_doctor["_id"]:
            raise HTTPException(
                status_code=403,
                detail="Doctor cannot create a medical record for another doctor"
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


# =========================================================
# Get medical records
# =========================================================

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

    # Default: get all medical records
    query = {}

    # Doctor: get only own medical records
    if current_user["role"] == "doctor":

        current_doctor = get_current_doctor(current_user)

        query = {
            "doctor_id": current_doctor["_id"]
        }

    records = list(
        medical_records_collection.aggregate([
            {
                "$match": query
            },
            {
                "$lookup": {
                    "from": "patients",
                    "localField": "patient_id",
                    "foreignField": "_id",
                    "as": "patient"
                }
            },
            {
                "$lookup": {
                    "from": "doctors",
                    "localField": "doctor_id",
                    "foreignField": "_id",
                    "as": "doctor"
                }
            },
            {
                "$unwind": {
                    "path": "$patient",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$unwind": {
                    "path": "$doctor",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "patient_id": 1,
                    "doctor_id": 1,
                    "appointment_id": 1,
                    "diagnosis": 1,
                    "treatment": 1,
                    "notes": 1,
                    "patient_name": "$patient.name",
                    "doctor_name": "$doctor.name"
                }
            }
        ])
    )

    # Convert ObjectIds to strings
    for record in records:

        if "patient_id" in record:
            record["patient_id"] = str(
                record["patient_id"]
            )

        if "doctor_id" in record:
            record["doctor_id"] = str(
                record["doctor_id"]
            )

        if "appointment_id" in record:
            record["appointment_id"] = str(
                record["appointment_id"]
            )

    return records


# =========================================================
# Update medical record
# =========================================================

@router.put("/medical-records/{record_id}")
def update_medical_record(
    record_id: str,
    record: MedicalRecordUpdate,
    current_user: dict = Depends(
        require_role("admin", "doctor")
    )
):

    # Convert medical record ID
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

    # Doctor can update only own medical records
    current_doctor = None

    if current_user["role"] == "doctor":

        current_doctor = get_current_doctor(current_user)

        if existing_record["doctor_id"] != current_doctor["_id"]:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to update this medical record"
            )

    # Get only fields provided by the user
    update_data = record.model_dump(
        exclude_unset=True
    )

    # Check empty update
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="At least one field is required for update"
        )

    # =====================================================
    # Patient
    # =====================================================

    if "patient_id" in update_data:

        patient_object_id = get_patient_object_id(
            update_data["patient_id"]
        )

        update_data["patient_id"] = patient_object_id

    else:

        patient_object_id = existing_record["patient_id"]

    # =====================================================
    # Doctor
    # =====================================================

    if "doctor_id" in update_data:

        doctor_object_id = get_doctor_object_id(
            update_data["doctor_id"]
        )

        # Doctor cannot assign record to another doctor
        if (
            current_user["role"] == "doctor"
            and doctor_object_id != current_doctor["_id"]
        ):
            raise HTTPException(
                status_code=403,
                detail="Doctor cannot assign the medical record to another doctor"
            )

        update_data["doctor_id"] = doctor_object_id

    else:

        doctor_object_id = existing_record["doctor_id"]

    # =====================================================
    # Appointment
    # =====================================================

    if "appointment_id" in update_data:

        appointment_object_id = get_appointment_object_id(
            update_data["appointment_id"]
        )

        update_data["appointment_id"] = appointment_object_id

    else:

        appointment_object_id = existing_record[
            "appointment_id"
        ]

        appointment = appointments_collection.find_one(
            {"_id": appointment_object_id}
        )

        if not appointment:
            raise HTTPException(
                status_code=404,
                detail="Appointment not found"
            )

    # If appointment_id was supplied, get appointment
    if "appointment_id" in update_data:

        appointment = appointments_collection.find_one(
            {"_id": appointment_object_id}
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

    # Update only provided fields
    medical_records_collection.update_one(
        {"_id": record_object_id},
        {"$set": update_data}
    )

    return {
        "message": "Medical record updated successfully"
    }


# =========================================================
# Delete medical record
# =========================================================

@router.delete("/medical-records/{record_id}")
def delete_medical_record(
    record_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Convert medical record ID
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