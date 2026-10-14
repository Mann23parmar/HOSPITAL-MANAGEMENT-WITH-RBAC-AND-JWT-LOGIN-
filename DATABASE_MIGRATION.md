# MongoDB index migration

Importing the application no longer creates indexes. Run the index migration
deliberately before deploying a version that depends on the unique constraints.
The migration checks existing index definitions and tests every unique index
against a temporary collection using MongoDB's own index implementation. This
preserves the behavior of compound, partial, sparse, missing/null, and array
keys without editing live records.

## Deployment order

1. Back up the database.
2. From the project root, run:

   ```powershell
   .\venv\Scripts\python.exe -m scripts.migrate_indexes
   ```

3. If duplicates are reported, resolve them manually after reviewing the
   collection, index, key, and document IDs in the report. The migration never
   chooses a record to keep, deletes records, or merges records.
4. Rerun the command until it reports success.
5. Start the FastAPI application.

Stop application writes while migrating. The migration pre-checks all current
data before creating any indexes, but a concurrent write between the pre-check
and index creation can still make MongoDB reject a unique index. If that
happens, the command reports the failure; some earlier indexes may have been
created. Resolve the data or deployment issue, then rerun the idempotent
migration.

The migration also preserves the existing TTL indexes. A successful command
means all declared indexes were verified against their expected key patterns
and options. A normal application startup only verifies database connectivity
when the health endpoint is requested; it does not run or certify this
migration.
