from datetime import date

from bson import ObjectId
from fastapi import HTTPException
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
from app.schemas.patient import PatientCreate, PatientUpdate, age_from_date_of_birth
from app.services.audit_service import create_audit_log


def create_patient(patient: PatientCreate, current_user: dict):
    existing_patient = patients_collection.find_one({"phone": patient.phone})
    if existing_patient:
        raise HTTPException(
            status_code=400, detail="Patient with this phone number already exists"
        )
    patient_data = patient.model_dump()
    patient_data["date_of_birth"] = patient.date_of_birth.isoformat()
    patient_data["created_by"] = ObjectId(current_user["user_id"])
    try:
        result = patients_collection.insert_one(patient_data)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409, detail="Patient with this phone number already exists"
        )
    create_audit_log(
        action="CREATE",
        collection="patients",
        record_id=str(result.inserted_id),
        current_user=current_user,
    )
    return {"message": "Patient created successfully"}


def get_patients(current_user: dict, skip: int = 0, limit: int = 10):
    query = {}
    if current_user["role"] == "doctor":
        doctor = get_current_doctor(current_user)
        patient_ids = appointments_collection.distinct(
            "patient_id", {"doctor_id": doctor["_id"]}
        )
        query = {"_id": {"$in": patient_ids}}
    patients = list(
        patients_collection.find(
            query,
            {"_id": 0, "_pending_reference_writes": 0, "_pending_reference_leases": 0},
        ).sort("_id", 1).skip(skip).limit(limit)
    )
    for patient in patients:
        if "created_by" in patient:
            patient["created_by"] = str(patient["created_by"])
    return patients


def update_patient(patient_id: str, patient: PatientUpdate, current_user: dict):
    patient_object_id = get_object_id(patient_id, "patient")
    existing_patient = patients_collection.find_one({"_id": patient_object_id})
    if not existing_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    update_data = patient.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=400, detail="At least one field is required for update"
        )
    if "age" in update_data or "date_of_birth" in update_data:
        updated_age = update_data.get("age", existing_patient["age"])
        updated_birth_date = update_data.get(
            "date_of_birth",
            date.fromisoformat(existing_patient["date_of_birth"]),
        )
        expected_age = age_from_date_of_birth(updated_birth_date)
        if updated_age != expected_age:
            raise HTTPException(
                status_code=400,
                detail=f"Age must match date of birth; the calculated age is {expected_age}",
            )
    if "phone" in update_data:
        existing_phone = patients_collection.find_one(
            {"phone": update_data["phone"], "_id": {"$ne": patient_object_id}}
        )
        if existing_phone:
            raise HTTPException(
                status_code=400, detail="Patient with this phone number already exists"
            )
    if "date_of_birth" in update_data:
        update_data["date_of_birth"] = update_data["date_of_birth"].isoformat()
    try:
        update_result = patients_collection.update_one(
            {"_id": patient_object_id}, {"$set": update_data}
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409, detail="Patient with this phone number already exists"
        )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    create_audit_log(
        action="UPDATE",
        collection="patients",
        record_id=str(patient_object_id),
        current_user=current_user,
    )
    return {"message": "Patient updated successfully"}


def delete_patient(patient_id: str, current_user: dict):
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
        raise HTTPException(status_code=404, detail="Patient not found")
    create_audit_log(
        action="DELETE",
        collection="patients",
        record_id=str(patient_object_id),
        current_user=current_user,
    )
    return {"message": "Patient deleted successfully"}
