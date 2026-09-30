from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.database.connection import patients_collection
from app.core.rbac import require_role
from app.schemas.patient import PatientCreate, PatientUpdate


router = APIRouter()


# Create patient
@router.post("/patients")
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

    patient_data = patient.model_dump()

    # Store the ID of the logged-in user
    patient_data["created_by"] = ObjectId(
        current_user["user_id"]
    )

    patients_collection.insert_one(patient_data)

    return {
        "message": "Patient created successfully"
    }


# Get all patients
# Get all patients
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

    patients = list(
        patients_collection.find(
            {},
            {"_id": 0}
        )
    )

    for patient in patients:

        # Convert created_by ObjectId to string
        if "created_by" in patient:
            patient["created_by"] = str(
                patient["created_by"]
            )

    return patients
# Update patient
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
    try:
        patient_object_id = ObjectId(patient_id)

    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid patient ID"
        )

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

    # Update only the provided fields
    patients_collection.update_one(
        {"_id": patient_object_id},
        {
            "$set": update_data
        }
    )

    return {
        "message": "Patient updated successfully"
    }



# Delete patient
@router.delete("/patients/{patient_id}")
def delete_patient(
    patient_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Check patient ID
    try:
        patient_object_id = ObjectId(patient_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid patient ID"
        )

    result = patients_collection.delete_one(
        {"_id": patient_object_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return {
        "message": "Patient deleted successfully"
    }