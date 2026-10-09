from bson import ObjectId
from bson.errors import InvalidId
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.core.authorization import (
    get_current_doctor,
    get_existing_object_id,
    get_object_id,
    protect_references,
)

from app.database.connection import (
    prescriptions_collection,
    patients_collection,
    doctors_collection,
    medical_records_collection,
    medicines_collection
)

from app.core.rbac import require_role

from app.schemas.prescription import (
    PrescriptionCreate,
    PrescriptionUpdate
)
from app.services.audit_service import create_audit_log


router = APIRouter()


# Reusable medical record validation
def get_medical_record_object_id(medical_record_id: str):
    return get_existing_object_id(
        medical_record_id, medical_records_collection, "medical record"
    )


# Reusable medicine validation
def get_available_medicine(medicine_id: str):

    try:
        medicine_object_id = ObjectId(medicine_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid medicine ID"
        )

    medicine = medicines_collection.find_one({
        "_id": medicine_object_id
    })

    if not medicine:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    # Check medicine expiry
    expiry_date = date.fromisoformat(
        medicine["expiry_date"]
    )

    if expiry_date <= date.today():
        raise HTTPException(
            status_code=400,
            detail="Medicine has expired"
        )

    # Check medicine stock
    if medicine["quantity"] <= 0:
        raise HTTPException(
            status_code=400,
            detail="Medicine is out of stock"
        )

    return medicine


def _reconcile_expired_stock_reservations(medicine_object_id: ObjectId) -> None:
    """Repair abandoned reservations before the next stock operation."""
    now = datetime.now(timezone.utc)
    medicine = medicines_collection.find_one(
        {"_id": medicine_object_id},
        {"_prescription_reservation_leases": 1},
    )
    if not medicine:
        return

    for lease in medicine.get("_prescription_reservation_leases", []):
        expires_at = lease.get("expires_at")
        if expires_at and expires_at.replace(tzinfo=timezone.utc) > now:
            continue
        transition = prescriptions_collection.find_one(
            {"stock_transition.reservation_id": lease["lease_id"]}
        )
        if transition:
            recover_stock_transition(lease["lease_id"])
            continue
        lease_filter = {
            "_id": medicine_object_id,
            "_prescription_reservation_leases": {
                "$elemMatch": {"lease_id": lease["lease_id"], "expires_at": {"$lte": now}}
            },
        }
        prescription_exists = prescriptions_collection.find_one(
            {"stock_reservation_id": lease["lease_id"]}, {"_id": 1}
        )
        if lease.get("kind") == "return":
            medicines_collection.update_one(
                lease_filter,
                {"$pull": {"_prescription_reservation_leases": {"lease_id": lease["lease_id"]}}},
            )
            continue
        update = {"$pull": {"_prescription_reservation_leases": {"lease_id": lease["lease_id"]}}}
        if not prescription_exists:
            update["$inc"] = {"quantity": lease["quantity"]}
        result = medicines_collection.update_one(lease_filter, update)
        if result.modified_count and prescription_exists:
            prescriptions_collection.update_one(
                {"stock_reservation_id": lease["lease_id"]},
                {"$unset": {"stock_reservation_id": ""}},
            )


def recover_stock_transition(reservation_id: str) -> None:
    """Finish or roll back a medicine change interrupted between writes."""
    prescription = prescriptions_collection.find_one(
        {"stock_transition.reservation_id": reservation_id}
    )
    if not prescription:
        return

    transition = prescription["stock_transition"]
    previous_medicine_id = transition["previous_medicine_id"]
    target_medicine_id = transition["target_medicine_id"]
    quantity = transition["quantity"]

    if prescription["medicine_id"] == previous_medicine_id:
        # The prescription update did not commit, so return the new medicine's
        # reservation. The lease filter makes retries idempotent.
        restore_stock_reservation(target_medicine_id, reservation_id)
    elif prescription["medicine_id"] == target_medicine_id:
        # The prescription now uses the new medicine. Record the old-stock
        # return on that medicine atomically so a crash cannot apply it twice.
        medicines_collection.update_one(
            {
                "_id": previous_medicine_id,
                "_stock_restore_operations": {"$ne": reservation_id},
            },
            {
                "$inc": {"quantity": quantity},
                "$addToSet": {"_stock_restore_operations": reservation_id},
            },
        )
        if not medicines_collection.find_one({"_id": previous_medicine_id}):
            raise RuntimeError(
                "Cannot recover prescription stock transition: previous medicine is missing"
            )
        finish_stock_reservation(target_medicine_id, reservation_id)
    else:
        raise RuntimeError(
            "Cannot recover prescription stock transition: medicine changed unexpectedly"
        )

    finish_stock_reservation(previous_medicine_id, reservation_id)
    prescriptions_collection.update_one(
        {
            "_id": prescription["_id"],
            "stock_transition.reservation_id": reservation_id,
        },
        {"$unset": {"stock_transition": ""}},
    )


def reconcile_stock_transitions() -> None:
    """Recover incomplete medicine swaps before serving application requests."""
    transitions = prescriptions_collection.find(
        {"stock_transition": {"$exists": True}},
        {"stock_transition.reservation_id": 1},
    )
    for prescription in transitions:
        recover_stock_transition(prescription["stock_transition"]["reservation_id"])


def reconcile_expired_stock_reservations() -> None:
    """Recover any stock reservation abandoned before the previous shutdown."""
    reconcile_stock_transitions()
    for medicine in medicines_collection.find(
        {"_prescription_reservation_leases.0": {"$exists": True}},
        {"_id": 1},
    ):
        _reconcile_expired_stock_reservations(medicine["_id"])


def reserve_medicine_stock(
    medicine_object_id: ObjectId,
    quantity: int,
    reservation_id: str | None = None,
) -> str:
    """Atomically reserve stock and record an expiring, recoverable lease."""
    _reconcile_expired_stock_reservations(medicine_object_id)
    lease_id = reservation_id or str(uuid4())
    result = medicines_collection.update_one(
        {
            "_id": medicine_object_id,
            "quantity": {"$gte": quantity},
            "expiry_date": {"$gt": date.today().isoformat()},
        },
        {
            "$inc": {
                "quantity": -quantity,
            },
            "$push": {
                "_prescription_reservation_leases": {
                    "lease_id": lease_id,
                    "quantity": quantity,
                    "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
                }
            },
        },
    )
    if result.matched_count:
        return lease_id

    medicine = medicines_collection.find_one({"_id": medicine_object_id})
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    if date.fromisoformat(medicine["expiry_date"]) <= date.today():
        raise HTTPException(status_code=400, detail="Medicine has expired")
    if medicine["quantity"] <= 0:
        raise HTTPException(status_code=400, detail="Medicine is out of stock")
    raise HTTPException(
        status_code=400,
        detail="Requested quantity is greater than available stock",
    )


def protect_medicine_stock_return(medicine_id: ObjectId, lease_id: str) -> None:
    result = medicines_collection.update_one(
        {"_id": medicine_id},
        {
            "$push": {
                "_prescription_reservation_leases": {
                    "lease_id": lease_id,
                    "kind": "return",
                    "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
                }
            }
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Medicine not found")


def finish_stock_reservation(medicine_id: ObjectId, lease_id: str) -> None:
    medicines_collection.update_one(
        {"_id": medicine_id},
        {"$pull": {"_prescription_reservation_leases": {"lease_id": lease_id}}},
    )


def restore_stock_reservation(medicine_id: ObjectId, lease_id: str) -> None:
    medicine = medicines_collection.find_one(
        {"_id": medicine_id, "_prescription_reservation_leases.lease_id": lease_id},
        {"_prescription_reservation_leases": 1},
    )
    if not medicine:
        return
    lease = next(
        item for item in medicine.get("_prescription_reservation_leases", [])
        if item["lease_id"] == lease_id
    )
    medicines_collection.update_one(
        {"_id": medicine_id, "_prescription_reservation_leases.lease_id": lease_id},
        {
            "$inc": {"quantity": lease["quantity"]},
            "$pull": {"_prescription_reservation_leases": {"lease_id": lease_id}},
        },
    )


# Reusable prescription ID validation
def get_prescription_object_id(prescription_id: str):
    return get_object_id(prescription_id, "prescription")


# Create prescription
@router.post("/prescriptions", status_code=201)
def create_prescription(
    prescription: PrescriptionCreate,
    current_user: dict = Depends(
        require_role("admin", "doctor")
    )
):

    # If logged-in user is a doctor,
    # make sure they are creating the prescription for themselves
    if current_user["role"] == "doctor":

        current_doctor = get_current_doctor(current_user)

        try:
            requested_doctor_id = ObjectId(
                prescription.doctor_id
            )
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail="Invalid doctor ID"
            )

        if requested_doctor_id != current_doctor["_id"]:
            raise HTTPException(
                status_code=403,
                detail="Doctors can only create prescriptions for themselves"
            )

    # Validate patient
    patient_object_id = get_existing_object_id(
        prescription.patient_id, patients_collection, "patient"
    )

    # Validate doctor
    doctor_object_id = get_existing_object_id(
        prescription.doctor_id, doctors_collection, "doctor"
    )

    # Validate medical record
    medical_record_object_id = get_medical_record_object_id(
        prescription.medical_record_id
    )

    # Get medical record
    medical_record = medical_records_collection.find_one({
        "_id": medical_record_object_id
    })

    # Check medical record belongs to patient
    if medical_record["patient_id"] != patient_object_id:
        raise HTTPException(
            status_code=400,
            detail="Medical record does not belong to this patient"
        )

    # Check medical record belongs to doctor
    if medical_record["doctor_id"] != doctor_object_id:
        raise HTTPException(
            status_code=400,
            detail="Medical record does not belong to this doctor"
        )

    # Validate medicine
    # This checks:
    # 1. Medicine exists
    # 2. Medicine is not expired
    # 3. Medicine has stock available
    medicine = get_available_medicine(
        prescription.medicine_id
    )

    # Check requested quantity against available stock
    if prescription.quantity > medicine["quantity"]:
        raise HTTPException(
            status_code=400,
            detail="Requested quantity is greater than available stock"
        )

    medicine_object_id = medicine["_id"]

    # Prepare prescription document
    prescription_data = {
        "patient_id": patient_object_id,
        "doctor_id": doctor_object_id,
        "medical_record_id": medical_record_object_id,
        "medicine_id": medicine_object_id,
        "quantity": prescription.quantity,
        "dosage": prescription.dosage,
        "frequency": prescription.frequency,
        "duration": prescription.duration,
        "instructions": prescription.instructions
    }

    # Reduce medicine stock
    stock_lease_id = reserve_medicine_stock(medicine_object_id, prescription.quantity)
    prescription_data["stock_reservation_id"] = stock_lease_id

    # Compensate if insertion fails after the atomic stock reservation.
    try:
        with protect_references(
            (patients_collection, patient_object_id, "patient"),
            (doctors_collection, doctor_object_id, "doctor"),
            (medical_records_collection, medical_record_object_id, "medical record"),
        ):
            current_medical_record = medical_records_collection.find_one(
                {"_id": medical_record_object_id}
            )
            if (
                not current_medical_record
                or current_medical_record["patient_id"] != patient_object_id
                or current_medical_record["doctor_id"] != doctor_object_id
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Medical record changed while creating the prescription; reload and retry",
                )
            result = prescriptions_collection.insert_one(prescription_data)
    except Exception:
        restore_stock_reservation(medicine_object_id, stock_lease_id)
        raise

    finish_stock_reservation(medicine_object_id, stock_lease_id)
    prescriptions_collection.update_one(
        {"_id": result.inserted_id}, {"$unset": {"stock_reservation_id": ""}}
    )

    create_audit_log(
        action="UPDATE",
        collection="medicines",
        record_id=str(medicine_object_id),
        current_user=current_user
    )

    create_audit_log(
        action="CREATE",
        collection="prescriptions",
        record_id=str(result.inserted_id),
        current_user=current_user
    )

    return {
        "message": "Prescription created successfully"
    }


# Get prescriptions
@router.get("/prescriptions")
def get_prescriptions(
    current_user: dict = Depends(
        require_role(
            "admin",
            "doctor",
            "nurse"
        )
    )
):

    # Admin and nurse can see all prescriptions
    query = {}

    # Doctor can only see their own prescriptions
    if current_user["role"] == "doctor":

        current_doctor = get_current_doctor(current_user)

        query = {
            "doctor_id": current_doctor["_id"]
        }

    prescriptions = list(
        prescriptions_collection.find(
            query,
            {"_id": 0, "stock_reservation_id": 0, "stock_transition": 0}
        )
    )

    for prescription in prescriptions:

        # Patient information
        if "patient_id" in prescription:

            patient_id = str(
                prescription["patient_id"]
            )

            prescription["patient_id"] = patient_id

            patient = patients_collection.find_one({
                "_id": ObjectId(patient_id)
            })

            prescription["patient_name"] = (
                patient["name"]
                if patient
                else "Unknown"
            )

        # Doctor information
        if "doctor_id" in prescription:

            doctor_id = str(
                prescription["doctor_id"]
            )

            prescription["doctor_id"] = doctor_id

            doctor = doctors_collection.find_one({
                "_id": ObjectId(doctor_id)
            })

            prescription["doctor_name"] = (
                doctor["name"]
                if doctor
                else "Unknown"
            )

        # Medical record ID
        if "medical_record_id" in prescription:

            prescription["medical_record_id"] = str(
                prescription["medical_record_id"]
            )

        # Medicine information
        if "medicine_id" in prescription:

            medicine_id = str(
                prescription["medicine_id"]
            )

            prescription["medicine_id"] = medicine_id

            medicine = medicines_collection.find_one({
                "_id": ObjectId(medicine_id)
            })

            prescription["medicine_name"] = (
                medicine["name"]
                if medicine
                else "Unknown"
            )

    return prescriptions


# Update prescription
@router.put("/prescriptions/{prescription_id}")
def update_prescription(
    prescription_id: str,
    prescription: PrescriptionUpdate,
    current_user: dict = Depends(
        require_role("admin", "doctor")
    )
):

    # Validate prescription ID
    prescription_object_id = get_prescription_object_id(
        prescription_id
    )

    # Check prescription exists
    existing_prescription = prescriptions_collection.find_one({
        "_id": prescription_object_id
    })

    if not existing_prescription:
        raise HTTPException(
            status_code=404,
            detail="Prescription not found"
        )

    # If doctor is updating,
    # make sure prescription belongs to that doctor
    if current_user["role"] == "doctor":

        current_doctor = get_current_doctor(current_user)

        if existing_prescription["doctor_id"] != current_doctor["_id"]:
            raise HTTPException(
                status_code=403,
                detail="Doctors can only update their own prescriptions"
            )

    # Get only fields provided by the user
    update_data = prescription.model_dump(
        exclude_unset=True
    )

    # Prevent empty update
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="At least one field is required for update"
        )

    # Validate patient ID if provided
    if "patient_id" in update_data:

        patient_object_id = get_existing_object_id(
            update_data["patient_id"], patients_collection, "patient"
        )

        update_data["patient_id"] = patient_object_id

    else:

        patient_object_id = existing_prescription["patient_id"]

    # Validate doctor ID if provided
    if "doctor_id" in update_data:

        doctor_object_id = get_existing_object_id(
            update_data["doctor_id"], doctors_collection, "doctor"
        )

        # Doctor cannot assign prescription
        # to another doctor
        if current_user["role"] == "doctor":

            current_doctor = get_current_doctor(current_user)

            if doctor_object_id != current_doctor["_id"]:
                raise HTTPException(
                    status_code=403,
                    detail="Doctors cannot assign prescriptions to another doctor"
                )

        update_data["doctor_id"] = doctor_object_id

    else:

        doctor_object_id = existing_prescription["doctor_id"]

    # Validate medical record ID if provided
    if "medical_record_id" in update_data:

        medical_record_object_id = get_medical_record_object_id(
            update_data["medical_record_id"]
        )

        update_data["medical_record_id"] = (
            medical_record_object_id
        )

    else:

        medical_record_object_id = (
            existing_prescription["medical_record_id"]
        )

    # Get medical record
    medical_record = medical_records_collection.find_one({
        "_id": medical_record_object_id
    })

    if not medical_record:
        raise HTTPException(
            status_code=404,
            detail="Medical record not found"
        )

    # Check medical record belongs to patient
    if medical_record["patient_id"] != patient_object_id:
        raise HTTPException(
            status_code=400,
            detail="Medical record does not belong to this patient"
        )

    # Check medical record belongs to doctor
    if medical_record["doctor_id"] != doctor_object_id:
        raise HTTPException(
            status_code=400,
            detail="Medical record does not belong to this doctor"
        )

    # Validate medicine ID if provided
    replacement_medicine_id = None
    old_medicine_id = existing_prescription["medicine_id"]
    old_quantity = existing_prescription["quantity"]
    medicine_changed = False

    if "medicine_id" in update_data:
        medicine = get_available_medicine(update_data["medicine_id"])
        replacement_medicine_id = medicine["_id"]
        update_data["medicine_id"] = replacement_medicine_id
        medicine_changed = replacement_medicine_id != old_medicine_id

    # Compare the old stock-bearing fields to stop concurrent medicine changes
    # from both updating the prescription and reserving stock.
    update_filter = {
        "_id": prescription_object_id,
        "patient_id": existing_prescription["patient_id"],
        "doctor_id": existing_prescription["doctor_id"],
        "medical_record_id": existing_prescription["medical_record_id"],
        "stock_transition": {"$exists": False},
    }
    for field in update_data:
        if field in existing_prescription:
            update_filter[field] = existing_prescription[field]
    if current_user["role"] == "doctor":
        update_filter["doctor_id"] = current_doctor["_id"]
    if medicine_changed:
        update_filter.update({"medicine_id": old_medicine_id, "quantity": old_quantity})

    pending_references = []
    if patient_object_id != existing_prescription["patient_id"]:
        pending_references.append((patients_collection, patient_object_id, "patient"))
    if doctor_object_id != existing_prescription["doctor_id"]:
        pending_references.append((doctors_collection, doctor_object_id, "doctor"))
    pending_references.append(
        (medical_records_collection, medical_record_object_id, "medical record")
    )

    stock_lease_id = None
    if medicine_changed:
        stock_lease_id = str(uuid4())
        reserve_medicine_stock(
            replacement_medicine_id,
            old_quantity,
            reservation_id=stock_lease_id,
        )
        try:
            protect_medicine_stock_return(old_medicine_id, stock_lease_id)
        except Exception:
            restore_stock_reservation(replacement_medicine_id, stock_lease_id)
            raise
        transition = {
            "reservation_id": stock_lease_id,
            "previous_medicine_id": old_medicine_id,
            "target_medicine_id": replacement_medicine_id,
            "quantity": old_quantity,
        }
        claim_result = prescriptions_collection.update_one(
            update_filter,
            {"$set": {"stock_transition": transition}},
        )
        if claim_result.matched_count == 0:
            restore_stock_reservation(replacement_medicine_id, stock_lease_id)
            finish_stock_reservation(old_medicine_id, stock_lease_id)
            raise HTTPException(
                status_code=409,
                detail="Prescription changed concurrently; reload and retry",
            )
        update_filter.pop("stock_transition")
        update_filter["stock_transition.reservation_id"] = stock_lease_id

    try:
        with protect_references(*pending_references):
            current_medical_record = medical_records_collection.find_one(
                {"_id": medical_record_object_id}
            )
            if (
                not current_medical_record
                or current_medical_record["patient_id"] != patient_object_id
                or current_medical_record["doctor_id"] != doctor_object_id
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Medical record changed while updating the prescription; reload and retry",
                )
            update_result = prescriptions_collection.update_one(
                update_filter,
                {"$set": update_data},
            )
    except Exception:
        if medicine_changed:
            recover_stock_transition(stock_lease_id)
        raise

    if update_result.matched_count == 0:
        if medicine_changed:
            recover_stock_transition(stock_lease_id)
        raise HTTPException(
            status_code=409,
            detail="Prescription changed concurrently; reload and retry",
        )

    if medicine_changed:
        recover_stock_transition(stock_lease_id)

    create_audit_log(
        action="UPDATE",
        collection="prescriptions",
        record_id=str(prescription_object_id),
        current_user=current_user
    )

    return {
        "message": "Prescription updated successfully"
    }


# Delete prescription
@router.delete("/prescriptions/{prescription_id}")
def delete_prescription(
    prescription_id: str,
    current_user: dict = Depends(
        require_role("admin")
    )
):

    # Validate prescription ID
    prescription_object_id = get_prescription_object_id(
        prescription_id
    )

    # Delete prescription
    result = prescriptions_collection.delete_one({
        "_id": prescription_object_id,
        "stock_transition": {"$exists": False},
    })

    if result.deleted_count == 0:
        if prescriptions_collection.find_one({"_id": prescription_object_id}):
            raise HTTPException(
                status_code=409,
                detail="Prescription medicine is being updated; retry deletion",
            )
        raise HTTPException(
            status_code=404,
            detail="Prescription not found"
        )

    create_audit_log(
        action="DELETE",
        collection="prescriptions",
        record_id=str(prescription_object_id),
        current_user=current_user
    )

    return {
        "message": "Prescription deleted successfully"
    }



