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


# Helper function to get current doctor's profile
def get_current_doctor(current_user: dict):
    try:
        user_object_id = ObjectId(
            current_user["user_id"]
        )
    except InvalidId:
        raise HTTPException(
            status_code=401,
            detail="Invalid user ID"
        )

    doctor = doctors_collection.find_one({
        "user_id": user_object_id
    })

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found"
        )

    return doctor


# Create prescription
@router.post("/prescriptions")
def create_prescription(
    prescription: PrescriptionCreate,
    current_user: dict = Depends(
        require_role("admin", "doctor")
    )
):

    # If logged-in user is a doctor,
    # make sure they are creating the prescription for themselves
    if current_user["role"] == "doctor":
        current_doctor = get_current_doctor(current_user)

        try:
            requested_doctor_id = ObjectId(
                prescription.doctor_id
            )
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail="Invalid doctor ID"
            )

        if requested_doctor_id != current_doctor["_id"]:
            raise HTTPException(
                status_code=403,
                detail="Doctors can only create prescriptions for themselves"
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

    # Check patient exists
    patient = patients_collection.find_one({
        "_id": patient_object_id
    })

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
    doctor = doctors_collection.find_one({
        "_id": doctor_object_id
    })

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
    medical_record = medical_records_collection.find_one({
        "_id": medical_record_object_id
    })

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
    medicine = medicines_collection.find_one({
        "_id": medicine_object_id
    })

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


    # Insert prescription
    prescriptions_collection.insert_one(
        prescription_data
    )

    return {
        "message": "Prescription created successfully"
    }


# Get prescriptions
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

    # Admin and nurse can see all prescriptions
    query = {}

    # Doctor can only see their own prescriptions
    if current_user["role"] == "doctor":
        current_doctor = get_current_doctor(current_user)

        query = {
            "doctor_id": current_doctor["_id"]
        }


    prescriptions = list(
        prescriptions_collection.find(
            query,
            {"_id": 0}
        )
    )


    for prescription in prescriptions:

        # Patient information
        if "patient_id" in prescription:

            patient_id = str(
                prescription["patient_id"]
            )

            prescription["patient_id"] = patient_id

            patient = patients_collection.find_one({
                "_id": ObjectId(patient_id)
            })

            prescription["patient_name"] = (
                patient["name"]
                if patient
                else "Unknown"
            )


        # Doctor information
        if "doctor_id" in prescription:

            doctor_id = str(
                prescription["doctor_id"]
            )

            prescription["doctor_id"] = doctor_id

            doctor = doctors_collection.find_one({
                "_id": ObjectId(doctor_id)
            })

            prescription["doctor_name"] = (
                doctor["name"]
                if doctor
                else "Unknown"
            )


        # Medical record ID
        if "medical_record_id" in prescription:

            prescription["medical_record_id"] = str(
                prescription["medical_record_id"]
            )


        # Medicine information
        if "medicine_id" in prescription:

            medicine_id = str(
                prescription["medicine_id"]
            )

            prescription["medicine_id"] = medicine_id

            medicine = medicines_collection.find_one({
                "_id": ObjectId(medicine_id)
            })

            prescription["medicine_name"] = (
                medicine["name"]
                if medicine
                else "Unknown"
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
    existing_prescription = prescriptions_collection.find_one({
        "_id": prescription_object_id
    })

    if not existing_prescription:
        raise HTTPException(
            status_code=404,
            detail="Prescription not found"
        )


    # If doctor is updating,
    # make sure prescription belongs to that doctor
    if current_user["role"] == "doctor":

        current_doctor = get_current_doctor(current_user)

        if existing_prescription["doctor_id"] != current_doctor["_id"]:
            raise HTTPException(
                status_code=403,
                detail="Doctors can only update their own prescriptions"
            )


    # Get only fields provided by the user
    update_data = prescription.model_dump(
        exclude_unset=True
    )


    # Prevent empty update
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="At least one field is required for update"
        )


    # Validate patient ID if provided
    if "patient_id" in update_data:

        try:
            patient_object_id = ObjectId(
                update_data["patient_id"]
            )
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail="Invalid patient ID"
            )

        patient = patients_collection.find_one({
            "_id": patient_object_id
        })

        if not patient:
            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )

        update_data["patient_id"] = patient_object_id

    else:
        patient_object_id = existing_prescription["patient_id"]


    # Validate doctor ID if provided
    if "doctor_id" in update_data:

        try:
            doctor_object_id = ObjectId(
                update_data["doctor_id"]
            )
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail="Invalid doctor ID"
            )

        # Doctor cannot assign prescription
        # to another doctor
        if current_user["role"] == "doctor":

            current_doctor = get_current_doctor(current_user)

            if doctor_object_id != current_doctor["_id"]:
                raise HTTPException(
                    status_code=403,
                    detail="Doctors cannot assign prescriptions to another doctor"
                )


        doctor = doctors_collection.find_one({
            "_id": doctor_object_id
        })

        if not doctor:
            raise HTTPException(
                status_code=404,
                detail="Doctor not found"
            )

        update_data["doctor_id"] = doctor_object_id

    else:
        doctor_object_id = existing_prescription["doctor_id"]


    # Validate medical record ID if provided
    if "medical_record_id" in update_data:

        try:
            medical_record_object_id = ObjectId(
                update_data["medical_record_id"]
            )
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail="Invalid medical record ID"
            )

        medical_record = medical_records_collection.find_one({
            "_id": medical_record_object_id
        })

        if not medical_record:
            raise HTTPException(
                status_code=404,
                detail="Medical record not found"
            )

        update_data["medical_record_id"] = medical_record_object_id

    else:

        medical_record = medical_records_collection.find_one({
            "_id": existing_prescription["medical_record_id"]
        })

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


    # Validate medicine ID if provided
    if "medicine_id" in update_data:

        try:
            medicine_object_id = ObjectId(
                update_data["medicine_id"]
            )
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail="Invalid medicine ID"
            )

        medicine = medicines_collection.find_one({
            "_id": medicine_object_id
        })

        if not medicine:
            raise HTTPException(
                status_code=404,
                detail="Medicine not found"
            )

        update_data["medicine_id"] = medicine_object_id


    # Update only provided fields
    prescriptions_collection.update_one(
        {"_id": prescription_object_id},
        {"$set": update_data}
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
    result = prescriptions_collection.delete_one({
        "_id": prescription_object_id
    })


    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Prescription not found"
        )


    return {
        "message": "Prescription deleted successfully"
    }