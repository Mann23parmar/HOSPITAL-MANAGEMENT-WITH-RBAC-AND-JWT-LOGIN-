from pydantic import BaseModel, Field


class DoctorCreate(BaseModel):

    user_id: str = Field(
        ...,
        min_length=24,
        max_length=24,
        examples=["66f123456789abcdef123456"]
    )

    department_id: str = Field(
        ...,
        min_length=24,
        max_length=24,
        examples=["66f987654321abcdef654321"]
    )

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Rahul Sharma"]
    )

    specialization: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Cardiology"]
    )

    phone: str = Field(
        ...,
        min_length=10,
        max_length=15,
        examples=["9876543210"]
    )


class DoctorUpdate(BaseModel):

    user_id: str = Field(
        ...,
        min_length=24,
        max_length=24
    )

    department_id: str = Field(
        ...,
        min_length=24,
        max_length=24
    )

    name: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    specialization: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    phone: str = Field(
        ...,
        min_length=10,
        max_length=15
    )