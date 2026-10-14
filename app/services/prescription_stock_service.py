from datetime import date, datetime, timedelta, timezone
import logging
from uuid import uuid4

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from app.database.connection import medicines_collection, prescriptions_collection

logger = logging.getLogger(__name__)


class CorruptStockTransitionError(RuntimeError):
    """A transition cannot be reconciled without risking an incorrect stock change."""

    def __init__(self, prescription_id, reservation_id: str, reason: str):
        super().__init__(reason)
        self.prescription_id = prescription_id
        self.reservation_id = reservation_id


def _log_corrupt_transition(error: CorruptStockTransitionError) -> None:
    logger.error(
        "Stock transition recovery left pending: prescription_id=%s "
        "reservation_id=%s reason=%s",
        error.prescription_id,
        error.reservation_id,
        error,
    )


def get_available_medicine(medicine_id: str):

    try:
        medicine_object_id = ObjectId(medicine_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid medicine ID")

    medicine = medicines_collection.find_one({"_id": medicine_object_id})

    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    # Check medicine expiry
    expiry_date = date.fromisoformat(medicine["expiry_date"])

    if expiry_date <= date.today():
        raise HTTPException(status_code=400, detail="Medicine has expired")

    # Check medicine stock
    if medicine["quantity"] <= 0:
        raise HTTPException(status_code=400, detail="Medicine is out of stock")

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
            try:
                recover_stock_transition(lease["lease_id"])
            except CorruptStockTransitionError as error:
                _log_corrupt_transition(error)
            continue
        lease_filter = {
            "_id": medicine_object_id,
            "_prescription_reservation_leases": {
                "$elemMatch": {
                    "lease_id": lease["lease_id"],
                    "expires_at": {"$lte": now},
                }
            },
        }
        prescription_exists = prescriptions_collection.find_one(
            {"stock_reservation_id": lease["lease_id"]}, {"_id": 1}
        )
        if lease.get("kind") == "return":
            medicines_collection.update_one(
                lease_filter,
                {
                    "$pull": {
                        "_prescription_reservation_leases": {
                            "lease_id": lease["lease_id"]
                        }
                    }
                },
            )
            continue
        update = {
            "$pull": {
                "_prescription_reservation_leases": {"lease_id": lease["lease_id"]}
            }
        }
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
    if transition.get("action") == "delete":
        medicine_id = transition["previous_medicine_id"]
        medicines_collection.update_one(
            {
                "_id": medicine_id,
                "_stock_restore_operations": {"$ne": reservation_id},
            },
            {
                "$inc": {"quantity": transition["quantity"]},
                "$addToSet": {"_stock_restore_operations": reservation_id},
            },
        )
        if not medicines_collection.find_one({"_id": medicine_id}):
            raise RuntimeError(
                "Cannot recover deleted prescription stock: medicine is missing"
            )
        prescriptions_collection.delete_one(
            {
                "_id": prescription["_id"],
                "stock_transition.reservation_id": reservation_id,
            }
        )
        return

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
            raise CorruptStockTransitionError(
                prescription["_id"],
                reservation_id,
                "Cannot recover prescription stock transition: previous medicine is missing",
            )
        finish_stock_reservation(target_medicine_id, reservation_id)
    else:
        raise CorruptStockTransitionError(
            prescription["_id"],
            reservation_id,
            "Cannot recover prescription stock transition: medicine changed unexpectedly",
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
    """Recover valid swaps and leave unsafe transitions pending for investigation."""
    now = datetime.now(timezone.utc)
    transitions = prescriptions_collection.find(
        {
            "stock_transition": {"$exists": True},
            "$or": [
                {"stock_transition.expires_at": {"$exists": False}},
                {"stock_transition.expires_at": {"$lte": now}},
            ],
        },
        {"stock_transition.reservation_id": 1},
    )
    for prescription in transitions:
        reservation_id = prescription["stock_transition"]["reservation_id"]
        try:
            recover_stock_transition(reservation_id)
        except CorruptStockTransitionError as error:
            # Isolate known data corruption, but let database/unexpected errors fail startup.
            _log_corrupt_transition(error)


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
            "_prescription_reservation_leases.lease_id": {"$ne": lease_id},
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
    if any(
        lease.get("lease_id") == lease_id
        for lease in medicine.get("_prescription_reservation_leases", [])
    ):
        return lease_id
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
        item
        for item in medicine.get("_prescription_reservation_leases", [])
        if item["lease_id"] == lease_id
    )
    medicines_collection.update_one(
        {"_id": medicine_id, "_prescription_reservation_leases.lease_id": lease_id},
        {
            "$inc": {"quantity": lease["quantity"]},
            "$pull": {"_prescription_reservation_leases": {"lease_id": lease_id}},
        },
    )


def recover_stock_creation(medicine_id: ObjectId, lease_id: str) -> None:
    """Resolve an uncertain prescription insert without refunding committed stock."""
    committed = prescriptions_collection.find_one(
        {"stock_reservation_id": lease_id}, {"_id": 1}
    )
    if committed:
        finish_stock_reservation(medicine_id, lease_id)
        prescriptions_collection.update_one(
            {"_id": committed["_id"], "stock_reservation_id": lease_id},
            {"$unset": {"stock_reservation_id": ""}},
        )
    else:
        restore_stock_reservation(medicine_id, lease_id)
