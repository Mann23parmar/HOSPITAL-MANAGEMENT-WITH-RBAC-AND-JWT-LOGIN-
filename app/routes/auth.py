from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from pymongo.collation import Collation
from slowapi.util import get_remote_address

from app.schemas.user import UserLogin
from app.database.connection import (
    users_collection,
    revoked_tokens_collection,
)
from app.services.auth_service import (
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/login")
@limiter.limit("5/minute")
def login(user: UserLogin, request: Request):
    email = user.email

    stored_user = users_collection.find_one({
        "email": email
    }, collation=Collation(locale="en", strength=2))

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
        "sub": str(stored_user["_id"]),
    })

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    # Upsert makes repeated logout requests safe and idempotent.
    revoked_tokens_collection.update_one(
        {"jti": current_user["_token_jti"]},
        {
            "$setOnInsert": {
                "jti": current_user["_token_jti"],
                "expires_at": current_user["_token_expires_at"],
            }
        },
        upsert=True,
    )
    return {"message": "Logout successful"}
