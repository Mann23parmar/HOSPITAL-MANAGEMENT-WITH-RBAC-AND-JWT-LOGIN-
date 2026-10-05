from datetime import date

from pydantic import (
    BaseModel,
    Field,
    StrictInt,
    StrictStr,
    field_validator
)


def validate_date_of_birth(value):
    if value is not None and value >= date.today():
        raise ValueError(
            "Date of birth must be in the past"
        )

    return value


class PatientCreate(BaseModel):

    name: StrictStr = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["John Doe"]
    )

    age: StrictInt = Field(
        ...,
        gt=0,
        examples=[35]
    )

    gender: StrictStr = Field(
        ...,
        min_length=1,
        max_length=20,
        examples=["Male"]
    )

    phone: StrictStr = Field(
        ...,
        min_length=10,
        max_length=15,
        examples=["9876543210"]
    )

    address: StrictStr = Field(
        ...,
        min_length=5,
        max_length=200,
        examples=["Ahmedabad, Gujarat"]
    )

    date_of_birth: date = Field(
        ...,
        examples=["1990-01-15"]
    )

    @field_validator("date_of_birth")
    @classmethod
    def validate_patient_date_of_birth(cls, value):
        return validate_date_of_birth(value)


class PatientUpdate(BaseModel):

    name: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    age: StrictInt | None = Field(
        default=None,
        gt=0
    )

    gender: StrictStr | None = Field(
        default=None,
        min_length=1,
        max_length=20
    )

    phone: StrictStr | None = Field(
        default=None,
        min_length=10,
        max_length=15
    )

    address: StrictStr | None = Field(
        default=None,
        min_length=5,
        max_length=200
    )

    date_of_birth: date | None = Field(
        default=None
    )

    @field_validator("date_of_birth")
    @classmethod
    def validate_patient_date_of_birth(cls, value):
        return validate_date_of_birth(value)
    
    
