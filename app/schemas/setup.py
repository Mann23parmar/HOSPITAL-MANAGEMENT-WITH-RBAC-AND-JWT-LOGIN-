from pydantic import BaseModel, Field, StrictStr, field_validator


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

    invitation_token: StrictStr = Field(
        ...,
        min_length=20,
        examples=["Paste the token from your invitation link"]
    )
