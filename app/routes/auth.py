from fastapi import APIRouter, HTTPException

from app.schemas.user import UserLogin
from app.database.connection import users_collection
from app.services.auth_service import verify_password, create_access_token

router = APIRouter()


@router.post("/login")
def login(user: UserLogin):

    stored_user = users_collection.find_one({
        "email": user.email
    })

    if stored_user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    password_correct = verify_password(
        user.password,
        stored_user["password"]
    )

    if not password_correct:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    if not stored_user.get("is_active", True):
        raise HTTPException(
        status_code=403,
        detail="User account is inactive"
    )
    access_token = create_access_token({
        "sub": stored_user["email"],
        "role": stored_user["role"]
    })

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer"
    }