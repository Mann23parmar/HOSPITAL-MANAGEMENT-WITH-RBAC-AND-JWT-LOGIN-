# Audit Logging: Simple Guide

## What audit logging does

Whenever an audited create, update, or delete succeeds, the route calls the
shared `create_audit_log()` function in `app/services/audit_service.py`. That
function adds a short activity record to MongoDB's `audit_logs` collection.

```text
CRUD route succeeds
        |
        v
create_audit_log(action, collection, record_id, current_user)
        |
        v
audit_logs collection receives one activity record
```

For example, creating a department calls the audit function with action
`CREATE`, collection `departments`, the inserted document's ID, and the
authenticated user's identity and role.

## What an audit record contains

- MongoDB's automatic `_id` field for the audit document.
- `who`: the available user identity. The user schema has no name field, so
  the email is used instead of making up a display name.
- `role`: the user's role, such as `admin` or `doctor`.
- `action`: `CREATE`, `UPDATE`, or `DELETE`.
- `collection`: the underlying collection name; the message uses a friendly
  resource name, such as `Department` for `departments`.
- `record_id`: the ID of the affected document.
- `timestamp`: when the audit record was made, stored in UTC.

These are the only fields written by the audit service. It does not include
passwords, whole MongoDB documents, email duplicates, or detailed old/new
field values. A readable message can be generated from these fields with
`format_audit_message()`; the message itself is not stored in MongoDB.

## Where audit calls are used

The routes call the same audit function for users, patients, appointments,
departments, doctors, nurses, medical records, medicines, prescriptions, and
patient vitals. Deleting a doctor or nurse also deactivates their linked user
account, so that account update is logged too. Creating a prescription logs
both the prescription and the resulting medicine stock update.

The initial admin setup is unauthenticated. Its audit entry uses the submitted
admin email and the `admin` role because there is no authenticated
`current_user` at that point. Read-only requests and login are not CRUD changes
and are not logged.

## If audit logging fails

Audit logging is best-effort. If MongoDB rejects an audit insert, the service
reports the exception through the server logger. A successful CRUD operation
still returns its normal API response.

## How to view entries in MongoDB Compass

1. Open the `hospital_management` database.
2. Refresh the collection list if needed.
3. Open `audit_logs`, then its **Documents** tab.
4. Use `who`, `role`, `action`, `collection`, and `timestamp` to read the
   activity. The service's `format_audit_message()` helper can format them
   into a sentence.

MongoDB creates `audit_logs` when the first audit entry is inserted. Actions
that happened before their routes were connected to audit logging are not
recorded retroactively.
