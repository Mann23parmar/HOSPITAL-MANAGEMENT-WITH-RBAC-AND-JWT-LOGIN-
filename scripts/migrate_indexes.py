"""Run the explicit MongoDB index pre-check and migration."""

import sys

from pymongo import MongoClient

from app.core.config import settings
from app.database.index_migration import IndexMigrationError, migrate_indexes


def main():
    client = MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=5000)
    try:
        database = client[settings.database_name]
        print(f"Checking indexes for database '{settings.database_name}'...")
        migrate_indexes(database)
        return 0
    except IndexMigrationError as error:
        print(f"Index migration failed:\n{error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Index migration failed due to a database or configuration error: {error}", file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
