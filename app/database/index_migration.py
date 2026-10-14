"""Explicit, repeatable migration for application MongoDB indexes."""

from dataclasses import dataclass
from uuid import uuid4

from pymongo.errors import BulkWriteError


@dataclass(frozen=True)
class IndexDefinition:
    collection: str
    keys: tuple[tuple[str, int], ...]
    options: dict

    @property
    def name(self):
        return self.options.get(
            "name", "_".join(f"{field}_{direction}" for field, direction in self.keys)
        )


INDEX_DEFINITIONS = (
    IndexDefinition("admin_invitations", (("token_hash", 1),), {"unique": True}),
    IndexDefinition("admin_invitations", (("expires_at", 1),), {"expireAfterSeconds": 0}),
    IndexDefinition(
        "prescriptions", (("stock_reservation_id", 1),),
        {"unique": True, "sparse": True, "name": "unique_stock_reservation_id"},
    ),
    IndexDefinition("revoked_tokens", (("jti", 1),), {"unique": True}),
    IndexDefinition("revoked_tokens", (("expires_at", 1),), {"expireAfterSeconds": 0}),
    IndexDefinition(
        "users", (("role", 1),),
        {"unique": True, "partialFilterExpression": {"role": "admin"}},
    ),
    IndexDefinition(
        "patients", (("phone", 1),),
        {"unique": True, "name": "unique_patient_phone"},
    ),
    IndexDefinition(
        "doctors", (("user_id", 1),),
        {"unique": True, "partialFilterExpression": {"_unique_user_profile": True}, "name": "unique_doctor_user"},
    ),
    IndexDefinition(
        "doctors", (("phone", 1),),
        {"unique": True, "partialFilterExpression": {"phone": {"$type": "string"}}, "name": "unique_doctor_phone"},
    ),
    IndexDefinition(
        "nurses", (("user_id", 1),),
        {"unique": True, "partialFilterExpression": {"user_id": {"$type": "objectId"}}, "name": "unique_nurse_user"},
    ),
    IndexDefinition(
        "nurses", (("phone", 1),),
        {"unique": True, "partialFilterExpression": {"phone": {"$type": "string"}}, "name": "unique_nurse_phone"},
    ),
    IndexDefinition(
        "departments", (("name", 1),),
        {"unique": True, "partialFilterExpression": {"name": {"$type": "string"}}, "name": "unique_department_name"},
    ),
    IndexDefinition(
        "medicines", (("name", 1), ("manufacturer", 1)),
        {
            "unique": True,
            "partialFilterExpression": {
                "name": {"$type": "string"},
                "manufacturer": {"$type": "string"},
            },
            "name": "unique_medicine_manufacturer",
        },
    ),
    IndexDefinition(
        "appointments", (("doctor_id", 1), ("appointment_date", 1), ("appointment_time", 1)),
        {
            "unique": True,
            "partialFilterExpression": {
                "status": "scheduled",
                "doctor_id": {"$type": "objectId"},
                "appointment_date": {"$type": "string"},
                "appointment_time": {"$type": "string"},
            },
            "name": "unique_scheduled_doctor_slot",
        },
    ),
    IndexDefinition(
        "medical_records", (("appointment_id", 1),),
        {"unique": True, "partialFilterExpression": {"appointment_id": {"$type": "objectId"}}, "name": "unique_medical_record_appointment"},
    ),
    IndexDefinition(
        "admin_invitations", (("active_invitation", 1),),
        {"unique": True, "partialFilterExpression": {"active_invitation": True}, "name": "one_active_admin_invitation"},
    ),
    IndexDefinition(
        "users", (("email_normalized", 1),),
        {"unique": True, "partialFilterExpression": {"email_normalized": {"$type": "string"}}, "name": "unique_normalized_user_email"},
    ),
)


class IndexMigrationError(RuntimeError):
    """An index could not be safely checked or created."""


class DuplicateIndexDataError(IndexMigrationError):
    def __init__(self, conflicts):
        self.conflicts = conflicts
        super().__init__(format_duplicate_conflicts(conflicts))


def _key_items(index):
    return tuple(index["key"].items())


def _check_existing_indexes(database):
    conflicts = []
    by_collection = {}
    for definition in INDEX_DEFINITIONS:
        if definition.collection not in by_collection:
            by_collection[definition.collection] = list(
                database[definition.collection].list_indexes()
            )
        indexes = by_collection[definition.collection]
        same_name = next(
            (item for item in indexes if item.get("name") == definition.name), None
        )
        same_keys = [item for item in indexes if _key_items(item) == definition.keys]
        existing = same_name or (same_keys[0] if same_keys else None)
        if existing is None:
            continue

        expected = definition.options
        actual_options = {
            "unique": existing.get("unique", False),
            "sparse": existing.get("sparse", False),
            "partialFilterExpression": existing.get("partialFilterExpression"),
            "expireAfterSeconds": existing.get("expireAfterSeconds"),
            "collation": existing.get("collation"),
            "hidden": existing.get("hidden", False),
        }
        expected_options = {
            "unique": expected.get("unique", False),
            "sparse": expected.get("sparse", False),
            "partialFilterExpression": expected.get("partialFilterExpression"),
            "expireAfterSeconds": expected.get("expireAfterSeconds"),
            "collation": expected.get("collation"),
            "hidden": expected.get("hidden", False),
        }
        if (
            existing.get("name") != definition.name
            or _key_items(existing) != definition.keys
            or actual_options != expected_options
        ):
            conflicts.append(
                f"{definition.collection}.{definition.name} conflicts with existing "
                f"index {existing.get('name')} (keys={dict(existing['key'])}, "
                f"options={actual_options})"
            )
    if conflicts:
        raise IndexMigrationError(
            "Existing index definitions conflict with the application requirements:\n- "
            + "\n- ".join(conflicts)
        )


def _paths_in_filter(expression):
    paths = set()
    for key, value in expression.items():
        if key.startswith("$"):
            if isinstance(value, dict):
                paths.update(_paths_in_filter(value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        paths.update(_paths_in_filter(item))
        else:
            paths.add(key)
    return paths


def _projection_for(definition):
    projection = {"_id": 1}
    for field, _ in definition.keys:
        projection[field] = 1
    projection.update(
        {
            field: 1
            for field in _paths_in_filter(
                definition.options.get("partialFilterExpression", {})
            )
        }
    )
    return projection


def _index_value(document, path):
    value = document
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return "<missing>"
        value = value[part]
    return value


def _precheck_unique_index(database, definition, batch_size=500):
    source = database[definition.collection]
    scratch_name = f"_idxcheck_{uuid4().hex}_{definition.name}"[:63]
    scratch = database[scratch_name]
    conflicts = []
    try:
        options = dict(definition.options)
        scratch.create_index(list(definition.keys), **options)
        cursor = source.find({}, _projection_for(definition)).batch_size(batch_size)
        batch = []
        for document in cursor:
            batch.append(document)
            if len(batch) >= batch_size:
                conflicts.extend(_insert_precheck_batch(scratch, definition, batch))
                batch = []
        if batch:
            conflicts.extend(_insert_precheck_batch(scratch, definition, batch))
    finally:
        scratch.drop()
    return conflicts


def _insert_precheck_batch(scratch, definition, documents):
    try:
        scratch.insert_many(documents, ordered=False)
        return []
    except BulkWriteError as error:
        write_errors = error.details.get("writeErrors", [])
        non_duplicate = [item for item in write_errors if item.get("code") not in (11000, 11001)]
        if non_duplicate:
            raise IndexMigrationError(
                f"Could not pre-check {definition.collection}.{definition.name}: {non_duplicate}"
            ) from error
        conflicts = []
        for item in write_errors:
            failed_document = documents[item["index"]]
            key_value = item.get("keyValue") or {
                field: _index_value(failed_document, field)
                for field, _ in definition.keys
            }
            previous = list(scratch.find(key_value, {"_id": 1}).limit(20))
            document_ids = [row["_id"] for row in previous]
            document_ids.append(failed_document["_id"])
            conflicts.append(
                {
                    "collection": definition.collection,
                    "index": definition.name,
                    "fields": [field for field, _ in definition.keys],
                    "key": key_value,
                    "document_ids": document_ids,
                }
            )
        return conflicts


def format_duplicate_conflicts(conflicts):
    lines = [
        "Duplicate data prevents required unique indexes from being created.",
        "Resolve the conflicting records manually; this migration never deletes or changes records.",
    ]
    for conflict in conflicts:
        lines.append(
            f"- collection={conflict['collection']}, index={conflict['index']}, "
            f"fields={conflict['fields']}, key={conflict['key']!r}, "
            f"document_ids={conflict['document_ids']!r}"
        )
    return "\n".join(lines)


def _create_real_index(collection, definition):
    return collection.create_index(list(definition.keys), **definition.options)


def migrate_indexes(database, output=print):
    """Pre-check every unique index, then create missing application indexes."""
    _check_existing_indexes(database)
    duplicate_conflicts = []
    for definition in INDEX_DEFINITIONS:
        if definition.options.get("unique"):
            duplicate_conflicts.extend(_precheck_unique_index(database, definition))
    if duplicate_conflicts:
        raise DuplicateIndexDataError(duplicate_conflicts)

    created = []
    skipped = []
    for definition in INDEX_DEFINITIONS:
        collection = database[definition.collection]
        existing_names = {item["name"] for item in collection.list_indexes()}
        if definition.name in existing_names:
            skipped.append(f"{definition.collection}.{definition.name}")
            continue
        try:
            _create_real_index(collection, definition)
        except Exception as error:
            raise IndexMigrationError(
                f"Failed to create {definition.collection}.{definition.name}: {error}. "
                "Some earlier indexes may already have been created; resolve the issue and rerun."
            ) from error
        created.append(f"{definition.collection}.{definition.name}")

    _check_existing_indexes(database)
    output(f"Index migration succeeded: created {len(created)}, already present {len(skipped)}.")
    return {"created": created, "skipped": skipped}
