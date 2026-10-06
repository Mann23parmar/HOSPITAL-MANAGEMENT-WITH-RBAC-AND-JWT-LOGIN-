from datetime import date

from pydantic import (
    BaseModel,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator
)
from app.schemas.update_payload import UpdatePayload


def validate_expiry_date(value):
    if value is not None and value <= date.today():
        raise ValueError(
            "Expiry date must be in the future"
        )

    return value


class MedicineCreate(BaseModel):

    name: StrictStr = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Paracetamol"]
    )

    description: StrictStr | None = Field(
        default=None,
        max_length=500,
        examples=["Used for fever and pain"]
    )

    manufacturer: StrictStr = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["ABC Pharma"]
    )

    price: StrictFloat = Field(
        ...,
        gt=0,
        examples=[50.0]
    )

    quantity: StrictInt = Field(
        ...,
        gt=0,
        examples=[100]
    )

    expiry_date: date = Field(
        ...,
        examples=["2027-12-31"]
    )

    @field_validator("expiry_date")
    @classmethod
    def validate_medicine_expiry_date(cls, value):
        return validate_expiry_date(value)


class MedicineUpdate(UpdatePayload):

    name: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    description: StrictStr | None = Field(
        default=None,
        max_length=500
    )

    manufacturer: StrictStr | None = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    price: StrictFloat | None = Field(
        default=None,
        gt=0
    )

    quantity: StrictInt | None = Field(
        default=None,
        gt=0
    )

    expiry_date: date | None = Field(
        default=None
    )

    @field_validator("expiry_date")
    @classmethod
    def validate_medicine_expiry_date(cls, value):
        return validate_expiry_date(value)
