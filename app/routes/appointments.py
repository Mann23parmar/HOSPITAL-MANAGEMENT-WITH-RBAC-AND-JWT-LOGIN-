from fastapi import APIRouter, Depends, Query
from app.core.rbac import require_role
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.services.appointments_service import (
    create_appointment as create_appointment_workflow,
    get_appointments as get_appointments_workflow,
    update_appointment as update_appointment_workflow,
    delete_appointment as delete_appointment_workflow,
)


router = APIRouter()


# Create appointment


@router.post("/appointments", status_code=201)
def create_appointment(
    appointment: AppointmentCreate,
    current_user: dict = Depends(require_role("admin", "receptionist")),
):
    return create_appointment_workflow(appointment, current_user)


@router.get("/appointments")
def get_appointments(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(
        require_role("admin", "doctor", "nurse", "receptionist")
    )
):
    return get_appointments_workflow(current_user, skip, limit)


@router.put("/appointments/{appointment_id}")
def update_appointment(
    appointment_id: str,
    appointment: AppointmentUpdate,
    current_user: dict = Depends(require_role("admin", "doctor", "receptionist")),
):
    return update_appointment_workflow(appointment_id, appointment, current_user)


@router.delete("/appointments/{appointment_id}")
def delete_appointment(
    appointment_id: str, current_user: dict = Depends(require_role("admin"))
):
    return delete_appointment_workflow(appointment_id, current_user)
