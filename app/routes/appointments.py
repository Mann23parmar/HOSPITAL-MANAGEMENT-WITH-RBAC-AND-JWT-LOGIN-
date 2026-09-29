from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.database.connection import (
    appointments_collection,
    patients_collection,
    doctors_collection
)

from app.core.rbac import require_role
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate


router = APIRouter()


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
        patient_object_id = ObjectId(appointment.patient_id)
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
        doctor_object_id = ObjectId(appointment.doctor_id)
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

    appointment_data = {
        "patient_id": patient_object_id,
        "doctor_id": doctor_object_id,
        "created_by": ObjectId(current_user["user_id"]),
        "appointment_date": appointment.appointment_date,
        "appointment_time": appointment.appointment_time,
        "reason": appointment.reason,
        "status": "scheduled"
    }

    appointments_collection.insert_one(
        appointment_data
    )

    return {
        "message": "Appointment created successfully"
    }


# Get all appointments
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

    appointments = list(
        appointments_collection.find(
            {},
            {"_id": 0}
        )
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

    doctor = doctors_collection.find_one(
        {"_id": doctor_object_id}
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # Validate appointment status
    allowed_statuses = {
        "scheduled",
        "completed",
        "cancelled"
    }

    if appointment.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid appointment status"
        )

    appointments_collection.update_one(
        {"_id": appointment_object_id},
        {
            "$set": {
                "patient_id": patient_object_id,
                "doctor_id": doctor_object_id,
                "appointment_date": appointment.appointment_date,
                "appointment_time": appointment.appointment_time,
                "reason": appointment.reason,
                "status": appointment.status
            }
        }
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