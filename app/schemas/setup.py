from pydantic import BaseModel, Field, StrictStr


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
        max_length=100,
        examples=["Admin@12345"]
    )