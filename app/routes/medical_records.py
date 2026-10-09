from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from app.core.authorization import (
    get_current_doctor,
    get_existing_object_id,
    protect_references,
    without_pending_references,
)
from app.database.connection import (
    medical_records_collection,
    prescriptions_collection,
    patients_collection,
    doctors_collection,
    appointments_collection
)
from app.core.rbac import require_role
from app.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordUpdate
)
from app.services.audit_service import create_audit_log


router = APIRouter()


# =========================================================
# Reusable validation functions
# =========================================================

def get_appointment_object_id(appointment_id: str):
    return get_existing_object_id(
        appointment_id, appointments_collection, "appointment"
    )


# =========================================================
# Create medical record
# =========================================================

@router.post("/medical-records", status_code=201)
def create_medical_record(
    record: MedicalRecordCreate,
    current_user: dict = Depends(
        require_role("admin", "doctor")
    )
):

    # Validate patient
    patient_object_id = get_existing_object_id(
        record.patient_id, patients_collection, "patient"
    )

    # Validate doctor
    doctor_object_id = get_existing_object_id(
        record.doctor_id, doctors_collection, "doctor"
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

    try:
        with protect_references(
            (patients_collection, patient_object_id, "patient"),
            (doctors_collection, doctor_object_id, "doctor"),
            (appointments_collection, appointment_object_id, "appointment"),
        ):
            appointment = appointments_collection.find_one(
                {"_id": appointment_object_id}
            )
            if (
                not appointment
                or appointment["patient_id"] != patient_object_id
                or appointment["doctor_id"] != doctor_object_id
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Appointment changed while creating the medical record; reload and retry",
                )
            result = medical_records_collection.insert_one(record_data)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="A medical record already exists for this appointment",
        )

    create_audit_log(
        action="CREATE",
        collection="medical_records",
        record_id=str(result.inserted_id),
        current_user=current_user
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

        patient_object_id = get_existing_object_id(
            update_data["patient_id"], patients_collection, "patient"
        )

        update_data["patient_id"] = patient_object_id

    else:

        patient_object_id = existing_record["patient_id"]

    # =====================================================
    # Doctor
    # =====================================================

    if "doctor_id" in update_data:

        doctor_object_id = get_existing_object_id(
            update_data["doctor_id"], doctors_collection, "doctor"
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
    relationships_changed = any(
        new_id != existing_record.get(field)
        for field, new_id in (
            ("patient_id", patient_object_id),
            ("doctor_id", doctor_object_id),
            ("appointment_id", appointment_object_id),
        )
    )
    if relationships_changed and prescriptions_collection.find_one(
        {"medical_record_id": record_object_id}
    ):
        raise HTTPException(
            status_code=409,
            detail="Medical record relationships cannot change while prescriptions reference it",
        )

    update_filter = {
        "_id": record_object_id,
        "patient_id": existing_record["patient_id"],
        "doctor_id": existing_record["doctor_id"],
        "appointment_id": existing_record["appointment_id"],
    }
    if current_user["role"] == "doctor":
        update_filter["doctor_id"] = current_doctor["_id"]
    if relationships_changed:
        update_filter["_pending_reference_writes"] = {"$in": [None, 0]}

    pending_references = []
    for collection, new_id, old_id, resource_name in (
        (patients_collection, patient_object_id, existing_record["patient_id"], "patient"),
        (doctors_collection, doctor_object_id, existing_record["doctor_id"], "doctor"),
        (appointments_collection, appointment_object_id, existing_record["appointment_id"], "appointment"),
    ):
        if new_id != old_id:
            pending_references.append((collection, new_id, resource_name))

    try:
        with protect_references(*pending_references):
            current_appointment = appointments_collection.find_one(
                {"_id": appointment_object_id}
            )
            if (
                not current_appointment
                or current_appointment["patient_id"] != patient_object_id
                or current_appointment["doctor_id"] != doctor_object_id
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Appointment changed while updating the medical record; reload and retry",
                )
            if relationships_changed and prescriptions_collection.find_one(
                {"medical_record_id": record_object_id}
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Medical record relationships cannot change while prescriptions reference it",
                )
            update_result = medical_records_collection.update_one(
                update_filter,
                {"$set": update_data},
            )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="A medical record already exists for this appointment",
        )

    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=409,
            detail="Medical record changed or reassigned concurrently; reload and retry",
        )

    create_audit_log(
        action="UPDATE",
        collection="medical_records",
        record_id=str(record_object_id),
        current_user=current_user
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

    if prescriptions_collection.find_one({"medical_record_id": record_object_id}):
        raise HTTPException(
            status_code=409,
            detail="Medical record cannot be deleted while prescriptions reference it",
        )

    result = medical_records_collection.delete_one(
        without_pending_references(record_object_id)
    )

    if result.deleted_count == 0:
        if medical_records_collection.find_one({"_id": record_object_id}):
            raise HTTPException(
                status_code=409,
                detail="Medical record is being updated concurrently; retry deletion",
            )
        raise HTTPException(
            status_code=404,
            detail="Medical record not found"
        )

    create_audit_log(
        action="DELETE",
        collection="medical_records",
        record_id=str(record_object_id),
        current_user=current_user
    )

    return {
        "message": "Medical record deleted successfully"
    }
