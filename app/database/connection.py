from pymongo import MongoClient

from app.core.config import settings


client = MongoClient(settings.MONGO_URL)

db = client[settings.database_name]


# Collections
users_collection = db["users"]
departments_collection = db["departments"]
doctors_collection = db["doctors"]
nurses_collection = db["nurses"]
patients_collection = db["patients"]
appointments_collection = db["appointments"]
medical_records_collection = db["medical_records"]
prescriptions_collection = db["prescriptions"]
medicines_collection = db["medicines"]
patient_vitals_collection = db["patient_vitals"]
audit_logs_collection = db["audit_logs"]
revoked_tokens_collection = db["revoked_tokens"]
admin_invitations_collection = db["admin_invitations"]
admin_invitations_collection.create_index("token_hash", unique=True)
admin_invitations_collection.create_index("expires_at", expireAfterSeconds=0)

# Temporary reservation IDs are used to recover stock if a prescription write
# is interrupted. Sparse indexing leaves existing prescription documents alone.
prescriptions_collection.create_index(
    "stock_reservation_id",
    unique=True,
    sparse=True,
    name="unique_stock_reservation_id",
)

# Revoked access tokens remain blocked until they expire, then MongoDB removes them.
revoked_tokens_collection.create_index("jti", unique=True)
revoked_tokens_collection.create_index("expires_at", expireAfterSeconds=0)

#allow only one admin to be created
users_collection.create_index(
    [("role", 1)],
    unique=True,
    partialFilterExpression={"role": "admin"}
)

# Enforce values that the route handlers also check. The indexes close the
# check-then-write race between concurrent requests.
patients_collection.create_index(
    "phone",
    unique=True,
    name="unique_patient_phone",
)
doctors_collection.create_index(
    "user_id",
    unique=True,
    partialFilterExpression={"_unique_user_profile": True},
    name="unique_doctor_user",
)
doctors_collection.create_index(
    "phone",
    unique=True,
    partialFilterExpression={"phone": {"$type": "string"}},
    name="unique_doctor_phone",
)
nurses_collection.create_index(
    "user_id",
    unique=True,
    partialFilterExpression={"user_id": {"$type": "objectId"}},
    name="unique_nurse_user",
)
nurses_collection.create_index(
    "phone",
    unique=True,
    partialFilterExpression={"phone": {"$type": "string"}},
    name="unique_nurse_phone",
)
departments_collection.create_index(
    "name",
    unique=True,
    partialFilterExpression={"name": {"$type": "string"}},
    name="unique_department_name",
)
medicines_collection.create_index(
    [("name", 1), ("manufacturer", 1)],
    unique=True,
    partialFilterExpression={
        "name": {"$type": "string"},
        "manufacturer": {"$type": "string"},
    },
    name="unique_medicine_manufacturer",
)

# A doctor can have only one scheduled appointment in a slot. Cancelled and
# completed appointments do not block the slot from being scheduled again.
appointments_collection.create_index(
    [("doctor_id", 1), ("appointment_date", 1), ("appointment_time", 1)],
    unique=True,
    partialFilterExpression={
        "status": "scheduled",
        "doctor_id": {"$type": "objectId"},
        "appointment_date": {"$type": "string"},
        "appointment_time": {"$type": "string"},
    },
    name="unique_scheduled_doctor_slot",
)

# The current data model allows one medical record per appointment.
medical_records_collection.create_index(
    "appointment_id",
    unique=True,
    partialFilterExpression={"appointment_id": {"$type": "objectId"}},
    name="unique_medical_record_appointment",
)

# Invitation generation is serialized by allowing only one active invitation.
admin_invitations_collection.create_index(
    "active_invitation",
    unique=True,
    partialFilterExpression={"active_invitation": True},
    name="one_active_admin_invitation",
)

# New user documents store a canonical email key. The partial index allows
# existing documents to remain in place while enforcing uniqueness for new writes.
users_collection.create_index(
    [("email_normalized", 1)],
    unique=True,
    partialFilterExpression={"email_normalized": {"$type": "string"}},
    name="unique_normalized_user_email",
)
