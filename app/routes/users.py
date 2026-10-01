from fastapi import APIRouter, HTTPException, Depends

from app.schemas.user import UserCreate
from app.database.connection import users_collection
from app.core.rbac import require_role
from app.services.auth_service import hash_password


router = APIRouter()


# Admin creates a user
@router.post("/users")
def create_user(
    user: UserCreate,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Check if email already exists
    existing_user = users_collection.find_one(
        {"email": user.email}
    )

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
        "is_active": True
    }

    users_collection.insert_one(user_data)

    return {
        "message": "User created successfully"
    }
    
    
    