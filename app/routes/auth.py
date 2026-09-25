#this file for authentication

from fastapi import APIRouter

from app.schemas.user import UserLogin
from app.database.connection import users_collection
from app.services.auth_service import verify_password, create_access_token


router = APIRouter()


@router.post("/login")
def login(user: UserLogin):

    stored_user = users_collection.find_one({
        "username": user.username
    })

    if stored_user is None:
        return {
            "message": "Invalid username or password"
        }
        
        

    password_correct = verify_password(
        user.password,
        stored_user["password"]
    )

    if not password_correct:
        return {
            "message": "Invalid username or password"
        }

    access_token = create_access_token({
        "sub": stored_user["username"],
        "role": stored_user["role"]
    })

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer"
    }