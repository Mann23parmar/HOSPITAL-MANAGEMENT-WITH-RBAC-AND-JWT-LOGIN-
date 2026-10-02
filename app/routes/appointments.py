from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from app.core.authorization import get_current_doctor
from app.database.connection import (
    appointments_collection,
    patients_collection,
    doctors_collection
)

from app.core.rbac import require_role
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate
)

router = APIRouter()


# Get current doctor's profile

# Create appointment
@router.post("/appointments")
def create_appointment(
    appointment: AppointmentCreate,
    current_user: dict = Depends(
        require_role("admin", "receptionist")
    )
):
    # Check patient ID
    try:
        patient_object_id = ObjectId(
            appointment.patient_id
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

    # Check doctor ID
    try:
        doctor_object_id = ObjectId(
            appointment.doctor_id
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

    # Prepare appointment data
    appointment_data = {
        "patient_id": patient_object_id,
        "doctor_id": doctor_object_id,
        "created_by": ObjectId(
            current_user["user_id"]
        ),
        "appointment_date": appointment.appointment_date.isoformat(),
        "appointment_time": appointment.appointment_time.isoformat(),
        "reason": appointment.reason,
        "status": "scheduled"
    }

    appointments_collection.insert_one(
        appointment_data
    )

    return {
        "message": "Appointment created successfully"
    }


# Get appointments
@router.get("/appointments")
def get_appointments(
    current_user: dict = Depends(
        require_role(
            "admin",
            "doctor",
            "nurse",
            "receptionist"
        )
    )
):
    # Default: show all appointments
    query = {}

    # Doctor: show only own appointments
    if current_user["role"] == "doctor":
        current_doctor = get_current_doctor(
            current_user
        )

        query = {
            "doctor_id": current_doctor["_id"]
        }

    appointments = list(
        appointments_collection.find(
            query,
            {"_id": 0}
        )
    )

    for appointment in appointments:

        # Patient
        if "patient_id" in appointment:
            patient_id = str(
                appointment["patient_id"]
            )

            appointment["patient_id"] = patient_id

            patient = patients_collection.find_one(
                {"_id": ObjectId(patient_id)}
            )

            appointment["patient_name"] = (
                patient["name"]
                if patient
                else "Unknown"
            )

        # Doctor
        if "doctor_id" in appointment:
            doctor_id = str(
                appointment["doctor_id"]
            )

            appointment["doctor_id"] = doctor_id

            doctor = doctors_collection.find_one(
                {"_id": ObjectId(doctor_id)}
            )

            appointment["doctor_name"] = (
                doctor["name"]
                if doctor
                else "Unknown"
            )

        # Created by
        if "created_by" in appointment:
            appointment["created_by"] = str(
                appointment["created_by"]
            )

    return appointments


# Update appointment
@router.put("/appointments/{appointment_id}")
def update_appointment(
    appointment_id: str,
    appointment: AppointmentUpdate,
    current_user: dict = Depends(
        require_role(
            "admin",
            "doctor",
            "receptionist"
        )
    )
):
    # Check appointment ID
    try:
        appointment_object_id = ObjectId(
            appointment_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid appointment ID"
        )

    # Check appointment exists
    existing_appointment = appointments_collection.find_one(
        {"_id": appointment_object_id}
    )

    if not existing_appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    # Doctor can update only own appointment
    current_doctor = None

    if current_user["role"] == "doctor":
        current_doctor = get_current_doctor(
            current_user
        )

        if existing_appointment["doctor_id"] != current_doctor["_id"]:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to update this appointment"
            )

    # Get only fields provided by user
    update_data = appointment.model_dump(
        exclude_unset=True
    )

    # Check empty update
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="At least one field is required for update"
        )

    # Effective patient ID
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

        patient = patients_collection.find_one(
            {"_id": patient_object_id}
        )

        if not patient:
            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )

        update_data["patient_id"] = patient_object_id

    # Effective doctor ID
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

        doctor = doctors_collection.find_one(
            {"_id": doctor_object_id}
        )

        if not doctor:
            raise HTTPException(
                status_code=404,
                detail="Doctor not found"
            )

        # Doctor cannot change appointment
        # to another doctor
        if (
            current_user["role"] == "doctor"
            and doctor_object_id != current_doctor["_id"]
        ):
            raise HTTPException(
                status_code=403,
                detail="Doctor cannot assign this appointment to another doctor"
            )

        update_data["doctor_id"] = doctor_object_id

    # Validate appointment status
    if "status" in update_data:

        allowed_statuses = {
            "scheduled",
            "completed",
            "cancelled"
        }

        if update_data["status"] not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid appointment status"
            )

    # Convert date to string
    if "appointment_date" in update_data:
        update_data["appointment_date"] = (
            update_data["appointment_date"].isoformat()
        )

    # Convert time to string
    if "appointment_time" in update_data:
        update_data["appointment_time"] = (
            update_data["appointment_time"].isoformat()
        )

    # Update appointment
    appointments_collection.update_one(
        {"_id": appointment_object_id},
        {"$set": update_data}
    )

    return {
        "message": "Appointment updated successfully"
    }


# Delete appointment
@router.delete("/appointments/{appointment_id}")
def delete_appointment(
    appointment_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):
    # Check appointment ID
    try:
        appointment_object_id = ObjectId(
            appointment_id
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid appointment ID"
        )

    result = appointments_collection.delete_one(
        {"_id": appointment_object_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    return {
        "message": "Appointment deleted successfully"
    }