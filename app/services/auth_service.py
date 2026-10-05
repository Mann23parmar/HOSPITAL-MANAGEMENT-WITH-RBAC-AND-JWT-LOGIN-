import bcrypt
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database.connection import users_collection
from app.core.config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES
)


# Hash password before storing it in MongoDB
def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")

    hashed_password = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed_password.decode("utf-8")


# Verify entered password with stored hashed password
def verify_password(
    password: str,
    hashed_password: str
) -> bool:
    password_bytes = password.encode("utf-8")
    hashed_password_bytes = hashed_password.encode("utf-8")

    return bcrypt.checkpw(
        password_bytes,
        hashed_password_bytes
    )


# Create JWT access token
def create_access_token(data: dict) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )


# JWT Bearer authentication
security = HTTPBearer()


# Get currently logged-in user
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        # JWT "sub" now contains user's email
        email = payload.get("sub")

        if email is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    # Find user using email
    current_user = users_collection.find_one({
        "email": email
    })

    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
    )
    return {
        "user_id": str(current_user["_id"]),
        "email": current_user["email"],
        "role": current_user["role"]
    }