from fastapi import APIRouter, HTTPException
from datetime import datetime
from zoneinfo import ZoneInfo
from app.schemas.setup import InitialAdminCreate
from app.database.connection import users_collection
from app.services.auth_service import hash_password


router = APIRouter()


@router.post("/setup/admin")
def create_initial_admin(admin: InitialAdminCreate):

    # Check whether an admin already exists
    existing_admin = users_collection.find_one({
        "role": "admin"
    })

    if existing_admin:
        raise HTTPException(
            status_code=403,
            detail="Initial admin setup has already been completed"
        )

    # Hash the password before storing it
    hashed_password = hash_password(admin.password)

    # Create the initial admin
    user_data = {
        "email": admin.email,
        "password": hashed_password,
        "role": "admin",
        "is_active": False,
        "created_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    }

    users_collection.insert_one(user_data)

    return {
        "message": "Initial admin created successfully"
    }
    
    
    
