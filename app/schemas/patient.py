from pydantic import BaseModel, Field


class PatientCreate(BaseModel):

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Amit Patel"]
    )

    date_of_birth: str = Field(
        ...,
        examples=["1990-05-15"]
    )

    gender: str = Field(
        ...,
        min_length=1,
        max_length=20,
        examples=["Male"]
    )

    phone: str = Field(
        ...,
        min_length=10,
        max_length=15,
        examples=["9876543210"]
    )

    address: str = Field(
        ...,
        min_length=5,
        max_length=200,
        examples=["Ahmedabad, Gujarat"]
    )

    emergency_contact: str = Field(
        ...,
        min_length=10,
        max_length=15,
        examples=["9876501234"]
    )

    blood_group: str = Field(
        ...,
        min_length=2,
        max_length=5,
        examples=["O+"]
    )


class PatientUpdate(BaseModel):

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    date_of_birth: str | None = None

    gender: str | None = Field(
        default=None,
        min_length=1,
        max_length=20
    )

    phone: str | None = Field(
        default=None,
        min_length=10,
        max_length=15
    )

    address: str | None = Field(
        default=None,
        min_length=5,
        max_length=200
    )

    emergency_contact: str | None = Field(
        default=None,
        min_length=10,
        max_length=15
    )

    blood_group: str | None = Field(
        default=None,
        min_length=2,
        max_length=5
    )