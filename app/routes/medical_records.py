from fastapi import APIRouter, Depends

from app.database.connection import db
from app.core.rbac import require_role
from app.schemas.medical_record import MedicalRecordCreate
from bson import ObjectId
from fastapi import HTTPException
from bson.errors import InvalidId
from app.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordUpdate
)

router = APIRouter()
patients_collection = db["patients"]
medical_records_collection = db["medical_records"]

#### this endpoint is for create medical _report
@router.post("/medical-records")
def create_medical_record(
    record: MedicalRecordCreate,
    current_user: dict = Depends(require_role("admin", "doctor"))
):
    try:
        patient = patients_collection.find_one(
            {"_id": ObjectId(record.patient_id)}
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid patient ID"
        )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    record_data = record.model_dump()
    medical_records_collection.insert_one(record_data)

    return {"message": "Medical record created successfully"}
    
#this endpoint is for read medical_report

@router.get("/medical-records")
def get_medical_records(
    current_user: dict = Depends(
        require_role("admin", "doctor", "nurse")
    )
):
    records = list(
        medical_records_collection.find({}, {"_id": 0})
    )

    return records


#this endpoint is for update medical_record
@router.put("/medical-records/{record_id}")
def update_medical_record(
    record_id: str,
    record: MedicalRecordUpdate,
    current_user: dict = Depends(
        require_role("admin", "doctor", "nurse")
    )
):
    # Check patient ID
    try:
        patient = patients_collection.find_one(
            {"_id": ObjectId(record.patient_id)}
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid patient ID"
        )

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # Check medical record ID
    try:
        result = medical_records_collection.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": record.model_dump()}
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid medical record ID"
        )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Medical record not found"
        )

    return {"message": "Medical record updated successfully"}
#this endpoint is for delete medical_record

@router.delete("/medical-records/{record_id}")
def delete_medical_record(
    record_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):
    result = medical_records_collection.delete_one(
        {"_id": ObjectId(record_id)}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Medical record not found"
        )

    return {
        "message": "Medical record deleted successfully"
    }
    