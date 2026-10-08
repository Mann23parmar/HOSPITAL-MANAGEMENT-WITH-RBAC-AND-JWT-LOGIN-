
import re

from pydantic import BaseModel, Field, StrictStr, field_validator
from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    RECEPTIONIST = "receptionist"


# Roles that an admin is allowed to create
class StaffRole(str, Enum):
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

    @field_validator("email")
    @classmethod
    def require_lowercase_email(cls, email: str) -> str:
        if email != email.lower():
            raise ValueError("Email must use lowercase letters")
        return email

    password: StrictStr = Field(
        ...,
        min_length=8,
        max_length=15,
    )

    @field_validator("password")
    @classmethod
    def enforce_password_policy(cls, password: str) -> str:
        if not any(character.isalpha() for character in password):
            raise ValueError("Password must contain at least one letter")
        if not any(character.isupper() for character in password):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(
            not character.isalnum() and not character.isspace()
            for character in password
        ):
            raise ValueError("Password must contain at least one special character")
        return password

    role: StaffRole


# User uses this schema to login
class UserLogin(BaseModel):

    email: StrictStr = Field(
        ...,
        min_length=5,
        max_length=100,
        examples=["doctor@example.com"]
    )

    @field_validator("email")
    @classmethod
    def validate_lowercase_email(cls, email: str) -> str:
        email = email.strip()
        if email != email.lower():
            raise ValueError("Email must use lowercase letters")

        email_pattern = r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+"
        if not re.fullmatch(email_pattern, email):
            raise ValueError("Enter a valid lowercase email address, such as abc@gmail.com")
        return email

    password: StrictStr = Field(
        ...,
        min_length=1,
        max_length=72,
    )


# Admin uses this schema to activate/deactivate a user
class UserStatusUpdate(BaseModel):

    is_active: bool
