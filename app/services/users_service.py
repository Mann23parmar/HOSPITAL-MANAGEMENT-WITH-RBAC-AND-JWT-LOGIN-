from fastapi import HTTPException
from bson import ObjectId
from pymongo.collation import Collation
from pymongo.errors import DuplicateKeyError
from app.database.connection import users_collection
from app.schemas.user import UserCreate, UserStatusUpdate
from app.services.auth_service import hash_password
from app.services.audit_service import create_audit_log


def create_user(user: UserCreate, current_user: dict):
    existing_user = users_collection.find_one(
        {"email": user.email}, collation=Collation(locale="en", strength=2)
    )
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")
    user_data = {
        "email": user.email,
        "email_normalized": user.email,
        "password": hash_password(user.password),
        "role": user.role.value,
        "is_active": True,
    }
    try:
        result = users_collection.insert_one(user_data)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email already registered")
    create_audit_log(
        action="CREATE",
        collection="users",
        record_id=str(result.inserted_id),
        current_user=current_user,
    )
    return {
        "message": "User created successfully",
        "user_id": str(result.inserted_id),
        "email": user.email,
        "role": user.role.value,
    }


def update_user_status(user_id: str, status: UserStatusUpdate, current_user: dict):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    if current_user["user_id"] == user_id:
        raise HTTPException(status_code=400, detail="You cannot change your own status")
    existing_user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    if existing_user.get("role") == "admin":
        raise HTTPException(
            status_code=403, detail="Admin user status cannot be changed"
        )
    update_data = {"is_active": status.is_active}
    users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
    create_audit_log(
        action="UPDATE",
        collection="users",
        record_id=user_id,
        current_user=current_user,
    )
    return {
        "message": "User status updated successfully",
        "user_id": user_id,
        "is_active": status.is_active,
    }
