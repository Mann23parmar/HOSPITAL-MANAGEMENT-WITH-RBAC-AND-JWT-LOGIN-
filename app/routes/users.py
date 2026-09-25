from fastapi import APIRouter, HTTPException, Depends
from app.schemas.user import UserCreate,UserLogin
from app.database.connection import users_collection
from app.core.rbac import require_role
from app.services.auth_service import hash_password
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token
)

router = APIRouter()


@router.post("/register")
def register_user(user: UserCreate):

    # here we Check if username already exists
    existing_user = users_collection.find_one(
        {"username": user.username}
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    # Hash password variable where we use hash password
    hashed_password = hash_password(user.password)

    # Create user document
    user_data = {
        "username": user.username,
        "password": hashed_password,
        "role": user.role
    }

    # Save all these user data to  MongoDB
    users_collection.insert_one(user_data)

    return {
        "message": "User registered successfully"
    }
    
#here i create login endpoint 
# @router.post('/login')
# def login_user(user:UserLogin):
    
#     #here first i find user is available or not
#     existing_user=users_collection.find_one(
#         {
#             "username":user.username
#         }
#     )
#     if not existing_user:
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid username or password"
#         )
#     #after find user we are verifing the user
    
#     password_correct = verify_password(
#         user.password,
#         existing_user["password"]
#     )

#     if not password_correct:
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid username or password"
#         )

#     # Create JWT
#     access_token = create_access_token({
#         "sub": str(existing_user["_id"]),
#         "username": existing_user["username"],
#         "role": existing_user["role"]
#     })

#     return {
#         "access_token": access_token,
#         "token_type": "bearer"
#     }
    
#this endpoint is to check admin how many users are registerd currently  
@router.get("/users/count")
def get_user_count(
    current_user: dict =Depends(require_role("admin"))
):
    count = users_collection.count_documents({})

    return {
        "total_users": count
    }
    
