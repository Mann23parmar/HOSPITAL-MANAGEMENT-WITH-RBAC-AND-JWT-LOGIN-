import bcrypt
import secrets
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from bson.errors import InvalidId

from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database.connection import users_collection, revoked_tokens_collection
from app.core.config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ISSUER,
    JWT_AUDIENCE,
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
    subject = data.get("sub")
    if not subject:
        raise ValueError("An access token requires a subject")
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    now = datetime.now(timezone.utc)
    to_encode = {
        "sub": str(subject),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": expire,
        "jti": secrets.token_urlsafe(32),
    }

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
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={
                "require_sub": True,
                "require_iss": True,
                "require_aud": True,
                "require_iat": True,
                "require_nbf": True,
                "require_exp": True,
                "require_jti": True,
            },
        )

        subject = payload["sub"]
        token_id = payload["jti"]
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    if not isinstance(subject, str) or not ObjectId.is_valid(subject):
        raise HTTPException(status_code=401, detail="Invalid token")
    if not isinstance(token_id, str) or not token_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    if revoked_tokens_collection.find_one({"jti": token_id}):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    try:
        current_user = users_collection.find_one({"_id": ObjectId(subject)})
    except (InvalidId, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token")

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
        "role": current_user["role"],
        "_token_jti": token_id,
        "_token_expires_at": datetime.fromtimestamp(payload["exp"], timezone.utc),
    }
