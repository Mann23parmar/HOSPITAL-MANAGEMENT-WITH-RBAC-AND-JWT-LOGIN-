from fastapi import APIRouter, Depends,HTTPException
from bson import ObjectId
from app.database.connection import db
from app.core.rbac import require_role
from app.schemas.patient import PatientCreate,PatientUpdate
from bson.errors import InvalidId
router = APIRouter()

patients_collection = db["patients"]


@router.post("/patients")
#here create-patient function which first take argument patient pydantic model and check current_user which is actully RBAC BECAUSE ONLY ADMIN AND RECEPTIONIST WILL ALLOW TO CREATEPATIENT
# def create_patient(
#     patient: PatientCreate,
#     current_user: dict = Depends(
#         require_role("admin", "receptionist")
#     )
# ):
    
#     patient_data = patient.model_dump()  #here we convert pydantic object to dictionary because it return only patient but we need dictionary like{name,age,gender} etc etc......

#     patients_collection.insert_one(patient_data)   #here i enter created patient into mongodb database
    
    

#     return {
#         "message": "Patient created successfully"
#     }
  
@router.post("/patients")
def create_patient(
    patient: PatientCreate,
    current_user: dict = Depends(require_role("admin", "receptionist"))
):
    existing_patient = patients_collection.find_one(
        {"phone": patient.phone}
    )

    if existing_patient:
        raise HTTPException(
            status_code=400,
            detail="Patient with this phone number already exists"
        )

    patient_data = patient.model_dump() ##here we convert pydantic object to dictionary because it return only patient but we need dictionary like{name,age,gender} etc etc......
    patients_collection.insert_one(patient_data)

    return {"message": "Patient created successfully"}
#this is read patient endpoint    
@router.get("/patients")
def get_patients(
    current_user: dict = Depends(
        require_role("admin", "doctor", "nurse", "receptionist")
    )
):
    patients = list(
        patients_collection.find({}, {"_id": 0})
    )

    return patients
#this is update patient endpoint which call when user want to update patient
@router.put("/patients/{patient_id}")
def update_patient(
    patient_id: str,
    patient: PatientUpdate,
    current_user: dict = Depends(
        require_role("admin", "doctor", "nurse", "receptionist")
    )
):
    # Check patient ID
    try:
        existing_patient = patients_collection.find_one(
            {"_id": ObjectId(patient_id)}
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid patient ID"
        )

    if not existing_patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # Check duplicate phone number
    duplicate_phone = patients_collection.find_one({
        "phone": patient.phone,
        "_id": {"$ne": ObjectId(patient_id)}
    })

    if duplicate_phone:
        raise HTTPException(
            status_code=400,
            detail="Another patient already uses this phone number"
        )

    # Update patient
    patients_collection.update_one(
        {"_id": ObjectId(patient_id)},
        {"$set": patient.model_dump()}
    )

    return {"message": "Patient updated successfully"}
#this is delete patients endpoint used to 
@router.delete("/patients/{patient_id}")
def delete_patient(
    patient_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):
    result = patients_collection.delete_one(
        {"_id": ObjectId(patient_id)}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return {
        "message": "Patient deleted successfully"
    }