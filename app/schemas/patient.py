from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, StrictStr, field_validator


class PatientCreate(BaseModel):

    name: StrictStr = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Amit Patel"]
    )

    date_of_birth: date = Field(
        ...,
        examples=["1990-05-15"]
    )

    gender: Literal["Male", "Female", "Other"] = Field(
        ...,
        examples=["Male"]
    )

    phone: StrictStr = Field(
        ...,
        min_length=10,
        max_length=15,
        pattern=r"^\d{10,15}$",   #meaning of this pattern is that it should be a string of digits with a length between 10 and 15 characters.
        examples=["9876543210"]
    )

    address: StrictStr = Field(
        ...,
        min_length=5,
        max_length=200,
        examples=["Ahmedabad, Gujarat"]
    )

    emergency_contact: StrictStr = Field(
        ...,
        min_length=10,
        max_length=15,
        pattern=r"^\d{10,15}$",
        examples=["9876501234"]
    )

    blood_group: Literal[
        "A+",
        "A-",
        "B+",
        "B-",
        "AB+",
        "AB-",
        "O+",
        "O-"
    ] = Field(
        ...,
        examples=["O+"]
    )

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date):
        if value >= date.today():
            raise ValueError(
                "Date of birth must be in the past"
            )

        return value


class PatientUpdate(BaseModel):

    name: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    date_of_birth: date | None = Field(
        default=None,
        examples=["1990-05-15"]
    )

    gender: Literal[
        "Male",
        "Female",
        "Other"
    ] | None = Field(
        default=None,
        examples=["Male"]
    )

    phone: StrictStr | None = Field(
        default=None,
        min_length=10,
        max_length=15,
        pattern=r"^\d{10,15}$"
    )

    address: StrictStr | None = Field(
        default=None,
        min_length=5,
        max_length=200
    )

    emergency_contact: StrictStr | None = Field(
        default=None,
        min_length=10,
        max_length=15,
        pattern=r"^\d{10,15}$"
    )

    blood_group: Literal[
        "A+",
        "A-",
        "B+",
        "B-",
        "AB+",
        "AB-",
        "O+",
        "O-"
    ] | None = Field(
        default=None
    )

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date | None):
        if value is not None and value >= date.today():
            raise ValueError(
                "Date of birth must be in the past"
            )

        return value