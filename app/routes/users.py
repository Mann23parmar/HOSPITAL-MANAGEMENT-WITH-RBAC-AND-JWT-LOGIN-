from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from zoneinfo import ZoneInfo

from app.schemas.user import UserCreate, UserStatusUpdate
from app.database.connection import users_collection
from app.core.rbac import require_role
from app.services.auth_service import hash_password


router = APIRouter()


# Admin creates a user
@router.post("/users")
def create_user(
    user: UserCreate,
    current_user: dict = Depends(require_role("admin"))
):
    # Admin users cannot be created from this endpoint
    

    # Check whether email already exists
    existing_user = users_collection.find_one({
        "email": user.email
    })

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # Hash password before storing
    hashed_password = hash_password(user.password)

    user_data = {
        "email": user.email,
        "password": hashed_password,
        "role": user.role.value,
        "is_active": True,
        "created_at": datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).isoformat()
    }

    users_collection.insert_one(user_data)

    return {
        "message": "User created successfully"
    }


# Admin changes user's active/inactive status
@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    status: UserStatusUpdate,
    current_user: dict = Depends(require_role("admin"))
):
    # Convert string ID to ObjectId
    from bson import ObjectId
    from bson.errors import InvalidId

    try:
        object_id = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID"
        )

    # Find user
    user = users_collection.find_one({
        "_id": object_id
    })

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Admin cannot change their own status
    if user_id == current_user["user_id"]:
        raise HTTPException(
            status_code=400,
            detail="Admin cannot change their own status"
        )

    # Update active/inactive status
    users_collection.update_one(
        {"_id": object_id},
        {
            "$set": {
                "is_active": status.is_active
            }
        }
    )

    return {
        "message": "User status updated successfully",
        "is_active": status.is_active
    }
    