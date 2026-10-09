from datetime import date

from pydantic import (
    BaseModel,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)
from app.schemas.update_payload import UpdatePayload


def validate_date_of_birth(value):
    if value is not None and value >= date.today():
        raise ValueError(
            "Date of birth must be in the past"
        )

    return value


def age_from_date_of_birth(date_of_birth: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def validate_age_matches_date_of_birth(age: int, date_of_birth: date) -> None:
    expected_age = age_from_date_of_birth(date_of_birth)
    if age != expected_age:
        raise ValueError(
            f"Age must match date of birth; the calculated age is {expected_age}"
        )


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
        le=120,
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
        max_length=16,
        pattern=r"^\+?[0-9]{10,15}$",
        examples=["9876543210"]
    )

    @field_validator("phone", mode="before")
    @classmethod
    def trim_phone(cls, value):
        return value.strip() if isinstance(value, str) else value

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

    @model_validator(mode="after")
    def validate_age_and_date_of_birth(self):
        validate_age_matches_date_of_birth(self.age, self.date_of_birth)
        return self


class PatientUpdate(UpdatePayload):

    name: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    age: StrictInt | None = Field(
        default=None,
        gt=0,
        le=120
    )

    gender: StrictStr | None = Field(
        default=None,
        min_length=1,
        max_length=20
    )

    phone: StrictStr | None = Field(
        default=None,
        min_length=10,
        max_length=16,
        pattern=r"^\+?[0-9]{10,15}$",
    )

    @field_validator("phone", mode="before")
    @classmethod
    def trim_phone(cls, value):
        return value.strip() if isinstance(value, str) else value

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

    @model_validator(mode="after")
    def validate_age_and_date_of_birth_when_both_provided(self):
        if self.age is not None and self.date_of_birth is not None:
            validate_age_matches_date_of_birth(self.age, self.date_of_birth)
        return self
    
    
