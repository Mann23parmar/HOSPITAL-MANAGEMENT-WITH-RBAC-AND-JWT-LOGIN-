from pydantic import BaseModel, Field, StrictStr
from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    RECEPTIONIST = "receptionist"


# Admin uses this schema to create a user
class UserCreate(BaseModel):

    email: StrictStr = Field(
        ...,
        min_length=5,
        max_length=100,
        examples=["doctor@example.com"]
    )

    password: StrictStr = Field(
        ...,
        min_length=8,
        max_length=100,
        examples=["Doctor@123"]
    )

    role: Role


# User uses this schema to login
class UserLogin(BaseModel):

    email: StrictStr = Field(
        ...,
        min_length=5,
        max_length=100,
        examples=["doctor@example.com"]
    )

    password: StrictStr = Field(
        ...,
        min_length=8,
        max_length=100,
        examples=["Doctor@123"])


# Admin uses this schema to activate/deactivate a user
class UserStatusUpdate(BaseModel):

    is_active: bool