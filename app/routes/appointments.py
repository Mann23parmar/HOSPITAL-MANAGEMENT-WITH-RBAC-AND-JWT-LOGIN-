from fastapi import APIRouter, Depends
from bson import ObjectId
from fastapi import HTTPException
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.database.connection import db
from app.core.rbac import require_role
from app.schemas.appointment import AppointmentCreate
from bson.errors import InvalidId
router = APIRouter()
#appointment table
appointments_collection = db["appointments"]
patients_collection = db["patients"]


@router.post("/appointments")
def create_appointment(
    appointment: AppointmentCreate,
    current_user: dict = Depends(require_role("admin", "receptionist"))
):
    try:
        patient = patients_collection.find_one({
            "_id": ObjectId(appointment.patient_id)
        })
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

    appointment_data = appointment.model_dump()

    appointments_collection.insert_one(appointment_data)

    return {"message": "Appointment created successfully"}
#this endpoint is for to read appointment and every role person can read it 
@router.get("/appointments")
def get_appointments(
    current_user: dict = Depends(
        require_role("admin", "doctor", "nurse", "receptionist")
    )
):
    appointments = list(
        appointments_collection.find({}, {"_id": 0})
    )

    return appointments



#this endpoint is for update appointment 
# @router.put("/appointments/{appointment_id}")
# def update_appointment(
#     appointment_id: str,
#     appointment: AppointmentUpdate,
#     current_user: dict = Depends(
#         require_role("admin", "doctor", "receptionist")
#     )
# ):
#     result = appointments_collection.update_one(
#         {"_id": ObjectId(appointment_id)},
#         {"$set": appointment.model_dump()}
#     )

#     if result.matched_count == 0:
#         raise HTTPException(
#             status_code=404,
#             detail="Appointment not found"
#         )

#     return {
#         "message": "Appointment updated successfully"
#     }
    
    
@router.put("/appointments/{appointment_id}")
def update_appointment(
    appointment_id: str,
    appointment: AppointmentUpdate,
    current_user: dict = Depends(
        require_role("admin", "doctor", "receptionist")
    )
):
    # Check patient ID
    try:
        patient = patients_collection.find_one(
            {"_id": ObjectId(appointment.patient_id)}
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

    # Check appointment ID
    try:
        result = appointments_collection.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": appointment.model_dump()}
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid appointment ID"
        )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    return {"message": "Appointment updated successfully"}
#this endpoint is for delete appointment

@router.delete("/appointments/{appointment_id}")
def delete_appointment(
    appointment_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):
    result = appointments_collection.delete_one(
        {"_id": ObjectId(appointment_id)}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    return {
        "message": "Appointment deleted successfully"
    }