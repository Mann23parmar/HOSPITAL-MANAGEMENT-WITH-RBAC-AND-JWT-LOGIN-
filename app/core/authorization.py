from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from app.database.connection import doctors_collection, nurses_collection


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


def get_current_nurse(current_user: dict):
    try:
        user_object_id = ObjectId(current_user["user_id"])
    except (InvalidId, KeyError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid user ID"
        )

    nurse = nurses_collection.find_one({
        "user_id": user_object_id
    })

    if not nurse:
        raise HTTPException(
            status_code=404,
            detail="Nurse profile not found"
        )

    return nurse
