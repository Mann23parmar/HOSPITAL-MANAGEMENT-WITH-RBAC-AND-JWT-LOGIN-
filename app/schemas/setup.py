from typing import Any

from pydantic import BaseModel, Field, StrictStr, field_validator

from app.schemas.user import normalize_and_validate_email, validate_password_policy


class InitialAdminCreate(BaseModel):
    email: StrictStr = Field(
        ...,
        min_length=5,
        max_length=100,
        examples=["admin@hospital.com"]
    )

    password: StrictStr = Field(
        ...,
        min_length=8,
        max_length=15,
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, email: Any) -> Any:
        return normalize_and_validate_email(email)

    @field_validator("password")
    @classmethod
    def enforce_password_policy(cls, password: str) -> str:
        return validate_password_policy(password)

    invitation_token: StrictStr = Field(
        ...,
        min_length=20,
        examples=["Paste the token from your invitation link"]
    )
