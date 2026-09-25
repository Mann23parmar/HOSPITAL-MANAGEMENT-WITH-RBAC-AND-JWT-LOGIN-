import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")

client = MongoClient(MONGO_URI)

db = client[DATABASE_NAME]

users_collection = db["users"]