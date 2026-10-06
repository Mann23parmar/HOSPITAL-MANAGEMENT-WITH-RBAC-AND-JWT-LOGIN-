from datetime import datetime, timezone
import logging

from app.database.connection import audit_logs_collection


logger = logging.getLogger(__name__)

ACTION_LABELS = {"create": "created","update": "updated","delete": "deleted",}

RESOURCE_LABELS = {
    "users": "User",
    "patients": "Patient",
    "appointments": "Appointment",
    "medical_records": "Medical Record",
    "medicines": "Medicine",
    "prescriptions": "Prescription",
    "patient_vitals": "Patient Vitals",
    "doctors": "Doctor",
    "nurses": "Nurse",
    "departments": "Department",
}


def format_audit_message(actor: str, role: str, action: str, resource: str, timestamp: datetime) -> str:
    action_label = ACTION_LABELS.get(action.lower(), action.lower())
    resource_label = RESOURCE_LABELS.get(resource,resource.replace("_", " ").title())
    role_label = role.replace("_", " ").title()
    formatted_time = timestamp.strftime("%d-%b-%Y at %I:%M %p UTC")

    return (f"{actor} ({role_label}) {action_label} {resource_label} "f"on {formatted_time}")


def create_audit_log(
    action: str,
    collection: str,
    record_id: str,
    current_user: dict):
    
    timestamp = datetime.now(timezone.utc)
    actor_email = current_user.get("email")
    actor = (
        current_user.get("display_name")
        or current_user.get("name")
        or actor_email
        or current_user.get("user_id")
        or "Unknown user")
    role = current_user.get("role", "unknown")

    audit_log = {
        "action": action,
        "collection": collection,
        "record_id": record_id,
        "who": actor,
        "role": role,
        "timestamp": timestamp,
    }

    try:
        audit_logs_collection.insert_one(audit_log)
    except Exception:
        # Auditing is best-effort: a logging outage must not change a
        # successful CRUD response, but it must be visible to operators.
        logger.exception(
            "Failed to write audit log for %s on %s record %s",
            action,
            collection,
            record_id,
        )
