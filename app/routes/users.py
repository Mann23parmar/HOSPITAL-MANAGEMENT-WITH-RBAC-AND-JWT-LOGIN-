from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from pymongo.collation import Collation
from pymongo.errors import DuplicateKeyError

from app.database.connection import users_collection
from app.schemas.user import UserCreate, UserStatusUpdate
from app.services.auth_service import get_current_user, hash_password
from app.core.rbac import require_role
from app.services.audit_service import create_audit_log


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post(
    "/",
    dependencies=[Depends(require_role("admin"))]
)
def create_user(
    user: UserCreate,
    current_user: dict = Depends(get_current_user)
):
    # Check existing legacy and normalized records before creating the user.
    existing_user = users_collection.find_one(
        {"email": user.email},
        collation=Collation(locale="en", strength=2),
    )
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    user_data = {
        "email": user.email,
        "email_normalized": user.email,
        "password": hash_password(user.password),
        "role": user.role.value,
        "is_active": True
    }

    try:
        result = users_collection.insert_one(user_data)
    except DuplicateKeyError:
        # The unique index resolves races where concurrent requests pass the lookup.
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    create_audit_log(
        action="CREATE",
        collection="users",
        record_id=str(result.inserted_id),
        current_user=current_user
    )

    return {
        "message": "User created successfully",
        "user_id": str(result.inserted_id),
        "email": user.email,
        "role": user.role.value
    }


@router.patch(
    "/{user_id}/status",
    dependencies=[Depends(require_role("admin"))]
)
def update_user_status(
    user_id: str,
    status: UserStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    # Validate ObjectId
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID"
        )

    # Prevent admin from changing their own status
    if current_user["user_id"] == user_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot change your own status"
        )

    # Find user
    existing_user = users_collection.find_one({
        "_id": ObjectId(user_id)
    })

    if not existing_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Prevent changing another admin's status
    if existing_user.get("role") == "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin user status cannot be changed"
        )

    update_data = {"is_active": status.is_active}

    # Update status
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": update_data
        }
    )

    create_audit_log(
        action="UPDATE",
        collection="users",
        record_id=user_id,
        current_user=current_user
    )

    return {
        "message": "User status updated successfully",
        "user_id": user_id,
        "is_active": status.is_active
    }
