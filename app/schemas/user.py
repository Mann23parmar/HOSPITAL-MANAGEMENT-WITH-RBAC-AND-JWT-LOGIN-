from pydantic import BaseModel

from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    RECEPTIONIST = "receptionist"

#user crete means register pydantic schema
class UserCreate(BaseModel):
    username: str
    password: str
    role: str


#user login pydantic schema
class UserLogin(BaseModel):
    username: str
    password: str
    