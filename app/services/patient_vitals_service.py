from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from app.database.connection import (
    patient_vitals_collection,
    patients_collection,
    nurses_collection,
    users_collection,
)
from app.core.authorization import (
    get_current_nurse,
    get_existing_object_id,
    protect_references,
    without_pending_references,
)
from app.schemas.patient_vitals import PatientVitalsCreate, PatientVitalsUpdate
from app.services.audit_service import create_audit_log


def get_nurse_object_id(nurse_id: str):
    try:
        nurse_object_id = ObjectId(nurse_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid nurse ID")
    nurse = nurses_collection.find_one({"_id": nurse_object_id})
    if not nurse:
        raise HTTPException(status_code=404, detail="Nurse not found")
    nurse_user = users_collection.find_one({"_id": nurse["user_id"]})
    if not nurse_user:
        raise HTTPException(status_code=404, detail="Nurse user account not found")
    if nurse_user["role"] != "nurse":
        raise HTTPException(
            status_code=400, detail="Selected user does not have nurse role"
        )
    return nurse_object_id


def get_vitals_object_id(vitals_id: str):
    try:
        return ObjectId(vitals_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid vitals ID")


def create_patient_vitals(vitals: PatientVitalsCreate, current_user: dict):
    patient_object_id = get_existing_object_id(
        vitals.patient_id, patients_collection, "patient"
    )
    nurse_object_id = get_nurse_object_id(vitals.nurse_id)
    if current_user["role"] == "nurse":
        current_nurse = get_current_nurse(current_user)
        if nurse_object_id != current_nurse["_id"]:
            raise HTTPException(
                status_code=403,
                detail="Nurses can only record vitals under their own profile",
            )
    vitals_data = {
        "patient_id": patient_object_id,
        "nurse_id": nurse_object_id,
        "blood_pressure": vitals.blood_pressure,
        "temperature": vitals.temperature,
        "pulse_rate": vitals.pulse_rate,
        "weight": vitals.weight,
    }
    with protect_references(
        (patients_collection, patient_object_id, "patient"),
        (nurses_collection, nurse_object_id, "nurse"),
    ):
        result = patient_vitals_collection.insert_one(vitals_data)
    create_audit_log(
        action="CREATE",
        collection="patient_vitals",
        record_id=str(result.inserted_id),
        current_user=current_user,
    )
    return {"message": "Patient vitals recorded successfully"}


def get_patient_vitals(current_user: dict):
    query = {}
    if current_user["role"] == "nurse":
        current_nurse = get_current_nurse(current_user)
        query["nurse_id"] = current_nurse["_id"]
    vitals = list(
        patient_vitals_collection.aggregate(
            [
                {"$match": query},
                {
                    "$lookup": {
                        "from": "patients",
                        "localField": "patient_id",
                        "foreignField": "_id",
                        "as": "patient",
                    }
                },
                {
                    "$lookup": {
                        "from": "nurses",
                        "localField": "nurse_id",
                        "foreignField": "_id",
                        "as": "nurse",
                    }
                },
                {"$unwind": {"path": "$patient", "preserveNullAndEmptyArrays": True}},
                {"$unwind": {"path": "$nurse", "preserveNullAndEmptyArrays": True}},
                {
                    "$project": {
                        "_id": 0,
                        "patient_id": 1,
                        "nurse_id": 1,
                        "blood_pressure": 1,
                        "temperature": 1,
                        "pulse_rate": 1,
                        "weight": 1,
                        "patient_name": "$patient.name",
                        "nurse_name": "$nurse.name",
                    }
                },
            ]
        )
    )
    for vital in vitals:
        if "patient_id" in vital:
            vital["patient_id"] = str(vital["patient_id"])
        if "nurse_id" in vital:
            vital["nurse_id"] = str(vital["nurse_id"])
    return vitals


def update_patient_vitals(
    vitals_id: str, vitals: PatientVitalsUpdate, current_user: dict
):
    vitals_object_id = get_vitals_object_id(vitals_id)
    existing_vitals = patient_vitals_collection.find_one({"_id": vitals_object_id})
    if not existing_vitals:
        raise HTTPException(status_code=404, detail="Patient vitals not found")
    current_nurse = None
    if current_user["role"] == "nurse":
        current_nurse = get_current_nurse(current_user)
        if existing_vitals.get("nurse_id") != current_nurse["_id"]:
            raise HTTPException(
                status_code=403, detail="Nurses can only update vitals they recorded"
            )
    update_data = vitals.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=400, detail="At least one field is required for update"
        )
    if "patient_id" in update_data:
        patient_object_id = get_existing_object_id(
            update_data["patient_id"], patients_collection, "patient"
        )
        update_data["patient_id"] = patient_object_id
    if "nurse_id" in update_data:
        nurse_object_id = get_nurse_object_id(update_data["nurse_id"])
        if current_nurse and nurse_object_id != current_nurse["_id"]:
            raise HTTPException(
                status_code=403, detail="Nurses cannot assign vitals to another nurse"
            )
        update_data["nurse_id"] = nurse_object_id
    update_filter = {"_id": vitals_object_id}
    if current_nurse:
        update_filter["nurse_id"] = current_nurse["_id"]
    pending_references = []
    if (
        "patient_id" in update_data
        and update_data["patient_id"] != existing_vitals["patient_id"]
    ):
        pending_references.append(
            (patients_collection, update_data["patient_id"], "patient")
        )
    if (
        "nurse_id" in update_data
        and update_data["nurse_id"] != existing_vitals["nurse_id"]
    ):
        pending_references.append((nurses_collection, update_data["nurse_id"], "nurse"))
    with protect_references(*pending_references):
        update_result = patient_vitals_collection.update_one(
            update_filter, {"$set": update_data}
        )
    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=409,
            detail="Vitals changed or reassigned concurrently; reload and retry",
        )
    create_audit_log(
        action="UPDATE",
        collection="patient_vitals",
        record_id=str(vitals_object_id),
        current_user=current_user,
    )
    return {"message": "Patient vitals updated successfully"}


def delete_patient_vitals(vitals_id: str, current_user: dict):
    vitals_object_id = get_vitals_object_id(vitals_id)
    result = patient_vitals_collection.delete_one(
        without_pending_references(vitals_object_id)
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Patient vitals not found")
    create_audit_log(
        action="DELETE",
        collection="patient_vitals",
        record_id=str(vitals_object_id),
        current_user=current_user,
    )
    return {"message": "Patient vitals deleted successfully"}
