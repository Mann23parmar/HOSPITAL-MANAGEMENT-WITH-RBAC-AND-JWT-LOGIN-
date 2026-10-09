from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from app.database.connection import (
    doctors_collection,
    nurses_collection,
    users_collection,
)


REFERENCE_LEASE_MINUTES = 30


def reference_lease_guard() -> dict:
    """Match documents with no currently active reference-write lease."""
    now = datetime.now(timezone.utc)
    return {
        "$or": [
            {"_pending_reference_leases": {"$exists": False}},
            {
                "_pending_reference_leases": {
                    "$not": {"$elemMatch": {"expires_at": {"$gt": now}}}
                }
            },
        ]
    }


@contextmanager
def protect_references(*references):
    """Protect referenced documents with leases that expire after a crash."""
    acquired = []
    lease_id = str(uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=REFERENCE_LEASE_MINUTES
    )
    try:
        for collection, object_id, resource_name in references:
            # Keep the lease array bounded when old requests died before release.
            collection.update_one(
                {"_id": object_id},
                {"$pull": {
                    "_pending_reference_leases": {
                        "expires_at": {"$lte": datetime.now(timezone.utc)}
                    }
                }},
            )
            result = collection.update_one(
                {"_id": object_id},
                {"$push": {
                    "_pending_reference_leases": {
                        "lease_id": lease_id,
                        "expires_at": expires_at,
                    }
                }},
            )
            if result.matched_count == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"{resource_name.capitalize()} not found",
                )
            acquired.append((collection, object_id, lease_id))
        yield
    finally:
        for collection, object_id, active_lease_id in reversed(acquired):
            collection.update_one(
                {"_id": object_id},
                {"$pull": {
                    "_pending_reference_leases": {"lease_id": active_lease_id}
                }},
            )


def without_pending_references(object_id: ObjectId) -> dict:
    return {"_id": object_id, **reference_lease_guard()}


def get_object_id(value: str, resource_name: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {resource_name} ID"
        )


def get_existing_object_id(value: str, collection, resource_name: str) -> ObjectId:
    object_id = get_object_id(value, resource_name)
    if not collection.find_one({"_id": object_id}):
        raise HTTPException(
            status_code=404,
            detail=f"{resource_name.capitalize()} not found"
        )
    return object_id


def get_user_object_id_for_role(user_id: str, role: str) -> ObjectId:
    user_object_id = get_object_id(user_id, "user")
    user = users_collection.find_one({"_id": user_object_id})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user["role"] != role:
        raise HTTPException(
            status_code=400,
            detail=f"Selected user does not have {role} role"
        )

    return user_object_id


def get_current_doctor(current_user: dict):
    try:
        user_object_id = ObjectId(
            current_user["user_id"]
        )
    except InvalidId:
        raise HTTPException(
            status_code=401,
            detail="Invalid user ID"
        )

    doctor = doctors_collection.find_one({
        "user_id": user_object_id
    })

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found"
        )

    return doctor


def get_current_nurse(current_user: dict):
    try:
        user_object_id = ObjectId(current_user["user_id"])
    except (InvalidId, KeyError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid user ID"
        )

    nurse = nurses_collection.find_one({
        "user_id": user_object_id
    })

    if not nurse:
        raise HTTPException(
            status_code=404,
            detail="Nurse profile not found"
        )

    return nurse
