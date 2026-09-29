from pydantic import BaseModel, Field
from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    RECEPTIONIST = "receptionist"


# Admin uses this schema to create a user
class UserCreate(BaseModel):

    email: str = Field(
        ...,
        min_length=5,
        max_length=100,
        examples=["doctor@example.com"]
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        examples=["Doctor@123"]
    )

    role: Role


# User uses this schema to login
class UserLogin(BaseModel):

    email: str = Field(
        ...,
        min_length=5,
        max_length=100,
        examples=["doctor@example.com"]
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        examples=["Doctor@123"]
    )