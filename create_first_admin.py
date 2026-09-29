from getpass import getpass

from app.database.connection import users_collection
from app.services.auth_service import hash_password


email = input("Enter admin email: ").strip()
password = getpass("Enter admin password: ")


existing_admin = users_collection.find_one({
    "email": email
})

if existing_admin:
    print("User with this email already exists.")
else:
    hashed_password = hash_password(password)

    user_data = {
        "email": email,
        "password": hashed_password,
        "role": "admin",
        "is_active": True
    }

    users_collection.insert_one(user_data)

    print("First admin created successfully.")