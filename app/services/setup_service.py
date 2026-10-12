import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.collation import Collation
from pymongo.errors import DuplicateKeyError
from app.database.connection import admin_invitations_collection, users_collection
from app.schemas.setup import InitialAdminCreate
from app.services.audit_service import create_audit_log
from app.services.auth_service import hash_password


def create_initial_admin(admin: InitialAdminCreate):
    existing_admin = users_collection.find_one({"role": "admin"})
    if existing_admin:
        raise HTTPException(
            status_code=403, detail="Initial admin setup has already been completed"
        )
    email = admin.email
    now = datetime.now(timezone.utc)
    existing_user = users_collection.find_one(
        {"email": email}, collation=Collation(locale="en", strength=2)
    )
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")
    token_hash = hashlib.sha256(admin.invitation_token.encode("utf-8")).hexdigest()
    invitation = admin_invitations_collection.find_one_and_update(
        {
            "token_hash": token_hash,
            "email": email,
            "used": False,
            "expires_at": {"$gt": now},
        },
        {"$set": {"used": True, "active_invitation": False, "used_at": now}},
        return_document=ReturnDocument.BEFORE,
    )
    if invitation is None:
        raise HTTPException(
            status_code=403,
            detail="Invitation is invalid, expired, already used, or does not match this email",
        )
    user_data = {
        "email": email,
        "email_normalized": email,
        "password": hash_password(admin.password),
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
    }
    try:
        result = users_collection.insert_one(user_data)
    except DuplicateKeyError as error:
        if "email_normalized" in (error.details or {}).get("keyPattern", {}):
            raise HTTPException(status_code=409, detail="Email already registered")
        raise HTTPException(
            status_code=403, detail="Initial admin setup has already been completed"
        )
    create_audit_log(
        action="CREATE",
        collection="users",
        record_id=str(result.inserted_id),
        current_user={"email": email, "role": "admin"},
    )
    return {"message": "Initial admin created successfully"}
