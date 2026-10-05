import os

from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")

client = MongoClient(MONGO_URL)


db = client[DATABASE_NAME]

# Collections(Tables)
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

