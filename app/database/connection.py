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

# Revoked access tokens remain blocked until they expire, then MongoDB removes them.
revoked_tokens_collection.create_index("jti", unique=True)
revoked_tokens_collection.create_index("expires_at", expireAfterSeconds=0)

#allow only one admin to be created
users_collection.create_index(
    [("role", 1)],
    unique=True,
    partialFilterExpression={"role": "admin"}
)
