from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.database.connection import medicines_collection
from app.core.rbac import require_role
from app.schemas.medicine import MedicineCreate, MedicineUpdate


router = APIRouter()


# Create medicine
@router.post("/medicines")
def create_medicine(
    medicine: MedicineCreate,
    current_user: dict = Depends(require_role("admin"))
):

    # Check duplicate medicine
    existing_medicine = medicines_collection.find_one(
        {
            "name": medicine.name,
            "manufacturer": medicine.manufacturer
        }
    )

    if existing_medicine:
        raise HTTPException(
            status_code=400,
            detail="This medicine from this manufacturer already exists"
        )

    medicine_data = medicine.model_dump()

    medicines_collection.insert_one(medicine_data)

    return {
        "message": "Medicine created successfully"
    }


# Get all medicines
@router.get("/medicines")
def get_medicines(
    current_user: dict = Depends(
        require_role(
            "admin",
            "doctor",
            "nurse",
            "receptionist"
        )
    )
):

    medicines = list(
        medicines_collection.find(
            {},
            {"_id": 0}
        )
    )

    return medicines


# Update medicine
@router.put("/medicines/{medicine_id}")
def update_medicine(
    medicine_id: str,
    medicine: MedicineUpdate,
    current_user: dict = Depends(require_role("admin"))
):

    # Check medicine ID
    try:
        medicine_object_id = ObjectId(medicine_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid medicine ID"
        )

    # Check medicine exists
    existing_medicine = medicines_collection.find_one(
        {"_id": medicine_object_id}
    )

    if not existing_medicine:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    # Get only fields provided by the user
    update_data = medicine.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="At least one field is required for update"
        )

    # Check duplicate medicine only when
    # name or manufacturer is being updated
    if "name" in update_data or "manufacturer" in update_data:

        medicine_name = update_data.get(
            "name",
            existing_medicine["name"]
        )

        medicine_manufacturer = update_data.get(
            "manufacturer",
            existing_medicine["manufacturer"]
        )

        duplicate_medicine = medicines_collection.find_one(
            {
                "name": medicine_name,
                "manufacturer": medicine_manufacturer,
                "_id": {"$ne": medicine_object_id}
            }
        )

        if duplicate_medicine:
            raise HTTPException(
                status_code=400,
                detail="Another medicine with this name and manufacturer already exists"
            )

    # Update only provided fields
    medicines_collection.update_one(
        {"_id": medicine_object_id},
        {"$set": update_data}
    )

    return {
        "message": "Medicine updated successfully"
    }


# Delete medicine
@router.delete("/medicines/{medicine_id}")
def delete_medicine(
    medicine_id: str,
    current_user: dict = Depends(require_role("admin"))
):

    # Check medicine ID
    try:
        medicine_object_id = ObjectId(medicine_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid medicine ID"
        )

    result = medicines_collection.delete_one(
        {"_id": medicine_object_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    return {
        "message": "Medicine deleted successfully"
    }