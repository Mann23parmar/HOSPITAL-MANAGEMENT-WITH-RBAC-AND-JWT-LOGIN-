
from typing import Any

from pydantic import BaseModel, Field, StrictStr, field_validator
from enum import Enum


def normalize_and_validate_email(email: Any) -> Any:
    if not isinstance(email, str):
        return email

    email = email.strip().lower()
    local_part, separator, domain = email.partition("@")
    if (
        not separator
        or not local_part
        or "@" in domain
        or "." not in domain
        or domain.startswith(".")
        or domain.endswith(".")
        or any(character.isspace() for character in email)
    ):
        raise ValueError("Enter a valid email address, such as abc@gmail.com")

    return email


def validate_password_policy(password: str) -> str:
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

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, email: Any) -> Any:
        return normalize_and_validate_email(email)

    password: StrictStr = Field(
        ...,
        min_length=8,
        max_length=15,
    )

    @field_validator("password")
    @classmethod
    def enforce_password_policy(cls, password: str) -> str:
        return validate_password_policy(password)

    role: StaffRole


# User uses this schema to login
class UserLogin(BaseModel):

    email: StrictStr = Field(
        ...,
        min_length=5,
        max_length=100,
        examples=["doctor@example.com"]
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, email: Any) -> Any:
        return normalize_and_validate_email(email)

    password: StrictStr = Field(
        ...,
        min_length=1,
        max_length=72,
    )


# Admin uses this schema to activate/deactivate a user
class UserStatusUpdate(BaseModel):

    is_active: bool
