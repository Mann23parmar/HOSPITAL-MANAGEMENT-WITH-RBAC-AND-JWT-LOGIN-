from fastapi import APIRouter, Depends

from app.database.connection import db
from app.core.rbac import require_role
from app.schemas.pharmacy import PharmacyCreate,PharmacyUpdate
from bson import ObjectId
from fastapi import HTTPException
from bson.errors import InvalidId
router = APIRouter()

pharmacy_collection = db["pharmacy"]

#this endpoint is for create pharmacy like name,medicine,quantity,price,expiry_Date
@router.post("/pharmacy")
def create_pharmacy(
    pharmacy: PharmacyCreate,
    current_user: dict = Depends(require_role("admin"))
):
    existing_medicine = pharmacy_collection.find_one({
        "medicine": pharmacy.medicine,
        "manufacturer": pharmacy.manufacturer
    })

    if existing_medicine:
        raise HTTPException(
            status_code=400,
            detail="This medicine from this manufacturer already exists"
        )

    pharmacy_data = pharmacy.model_dump()
    pharmacy_collection.insert_one(pharmacy_data)

    return {"message": "Pharmacy item created successfully"}

#this endpoint is for get data of pharmacy
@router.get("/pharmacy")
def get_pharmacy(
    current_user: dict = Depends(
        require_role("admin", "doctor", "nurse", "receptionist")
    )
):
    pharmacy = list(
        pharmacy_collection.find({}, {"_id": 0})
    )

    return pharmacy

#this endpoint is for update pharmacy

@router.put("/pharmacy/{pharmacy_id}")
def update_pharmacy(
    pharmacy_id: str,
    pharmacy: PharmacyUpdate,
    current_user: dict = Depends(require_role("admin"))
):
    # Check pharmacy ID
    try:
        existing_item = pharmacy_collection.find_one(
            {"_id": ObjectId(pharmacy_id)}
        )
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid pharmacy ID"
        )

    if not existing_item:
        raise HTTPException(
            status_code=404,
            detail="Pharmacy item not found"
        )

    # Check duplicate medicine + manufacturer
    duplicate_item = pharmacy_collection.find_one({
        "medicine": pharmacy.medicine,
        "manufacturer": pharmacy.manufacturer,
        "_id": {"$ne": ObjectId(pharmacy_id)}
    })

    if duplicate_item:
        raise HTTPException(
            status_code=400,
            detail="Another pharmacy item with this medicine and manufacturer already exists"
        )

    # Update
    pharmacy_collection.update_one(
        {"_id": ObjectId(pharmacy_id)},
        {"$set": pharmacy.model_dump()}
    )

    return {"message": "Pharmacy item updated successfully"}
    
#this endpoint is to delete pharmacy

@router.delete("/pharmacy/{pharmacy_id}")
def delete_pharmacy(
    pharmacy_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):
    result = pharmacy_collection.delete_one(
        {"_id": ObjectId(pharmacy_id)}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Pharmacy item not found"
        )

    return {
        "message": "Pharmacy item deleted successfully"
    }